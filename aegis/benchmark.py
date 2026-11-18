"""Offline, deterministic calibration smoke benchmark for robust anomaly scoring.

This benchmark measures statistical outlier classification only. It does not
measure vulnerability detection, and an anomaly must never be treated as a
security finding without independent security-property validation.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from .baseline import robust_anomaly_score

REFERENCE = (98.0, 101.0, 99.0, 102.0, 100.0, 97.0, 103.0, 100.0)


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    baseline: tuple[float, ...]
    value: float
    expected_anomaly: bool | None
    security_violation: bool
    description: str

    def __post_init__(self) -> None:
        if not self.case_id or len(self.case_id) > 64:
            raise ValueError("case_id must be 1..64 characters")
        if any(not math.isfinite(x) for x in self.baseline):
            raise ValueError("baseline values must be finite")
        if not math.isfinite(self.value):
            raise ValueError("observed value must be finite")
        if not self.baseline and self.expected_anomaly is not None:
            raise ValueError("an empty baseline must be labeled unscored")
        if self.baseline and self.expected_anomaly is None:
            raise ValueError("a non-empty baseline requires an anomaly label")


@dataclass(frozen=True)
class BenchmarkResult:
    case_id: str
    score: float | None
    predicted_anomaly: bool | None
    expected_anomaly: bool | None
    security_violation: bool


@dataclass(frozen=True)
class BenchmarkMetrics:
    threshold: float
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    scored: int
    unscored: int
    precision: float
    recall: float
    false_positive_rate: float
    accuracy: float


@dataclass(frozen=True)
class BenchmarkReport:
    results: tuple[BenchmarkResult, ...]
    metrics: BenchmarkMetrics


DEFAULT_CASES = (
    BenchmarkCase("nominal", REFERENCE, 100.0, False, False, "Reference median."),
    BenchmarkCase("benign_jitter", REFERENCE, 103.0, False, False, "Ordinary variation."),
    BenchmarkCase(
        "benign_upper_variation",
        REFERENCE,
        106.0,
        False,
        False,
        "Upper variation below the default threshold.",
    ),
    BenchmarkCase(
        "benign_latency_outlier",
        REFERENCE,
        108.0,
        True,
        False,
        "Statistical outlier without a security-property violation.",
    ),
    BenchmarkCase(
        "known_latency_regression",
        REFERENCE,
        112.0,
        True,
        False,
        "Injected latency regression in synthetic data.",
    ),
    BenchmarkCase(
        "extreme_latency_regression",
        REFERENCE,
        120.0,
        True,
        False,
        "Large statistical deviation.",
    ),
    BenchmarkCase(
        "zero_dispersion_nominal",
        (10.0, 10.0, 10.0),
        10.0,
        False,
        False,
        "Observed value equals a zero-MAD baseline.",
    ),
    BenchmarkCase(
        "zero_dispersion_deviation",
        (10.0, 10.0, 10.0),
        11.0,
        True,
        False,
        "Observed value differs from a zero-MAD baseline.",
    ),
    BenchmarkCase(
        "explicit_authz_violation",
        REFERENCE,
        100.0,
        False,
        True,
        "Security-property violation with nominal latency; anomaly scoring must not substitute for validation.",
    ),
    BenchmarkCase(
        "no_baseline",
        (),
        500.0,
        None,
        False,
        "No baseline; score is unavailable and the case is excluded from metrics.",
    ),
)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_benchmark(
    cases: Iterable[BenchmarkCase] = DEFAULT_CASES,
    threshold: float = 3.5,
) -> BenchmarkReport:
    """Evaluate labeled cases; missing baselines are abstentions, not negatives."""
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be finite and positive")
    items = tuple(cases)
    identifiers = [case.case_id for case in items]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("case_id values must be unique")

    results: list[BenchmarkResult] = []
    tp = fp = tn = fn = unscored = 0
    for case in items:
        if not case.baseline:
            results.append(
                BenchmarkResult(case.case_id, None, None, None, case.security_violation)
            )
            unscored += 1
            continue
        score = robust_anomaly_score(list(case.baseline), case.value)
        predicted = score >= threshold
        results.append(
            BenchmarkResult(
                case.case_id,
                score,
                predicted,
                case.expected_anomaly,
                case.security_violation,
            )
        )
        if case.expected_anomaly is True and predicted:
            tp += 1
        elif case.expected_anomaly is True:
            fn += 1
        elif case.expected_anomaly is False and predicted:
            fp += 1
        else:
            tn += 1

    scored = tp + fp + tn + fn
    metrics = BenchmarkMetrics(
        threshold=threshold,
        true_positive=tp,
        false_positive=fp,
        true_negative=tn,
        false_negative=fn,
        scored=scored,
        unscored=unscored,
        precision=_ratio(tp, tp + fp),
        recall=_ratio(tp, tp + fn),
        false_positive_rate=_ratio(fp, fp + tn),
        accuracy=_ratio(tp + tn, scored),
    )
    return BenchmarkReport(tuple(results), metrics)
