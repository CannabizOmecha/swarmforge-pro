import math

import pytest

from aegis.benchmark import DEFAULT_CASES, BenchmarkCase, evaluate_benchmark


def test_default_benchmark_reports_expected_confusion_counts():
    report = evaluate_benchmark()
    metrics = report.metrics
    assert (metrics.true_positive, metrics.false_positive) == (4, 0)
    assert (metrics.true_negative, metrics.false_negative) == (5, 0)
    assert metrics.scored == 9
    assert metrics.unscored == 1
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.false_positive_rate == 0.0
    assert metrics.accuracy == 1.0


def test_benign_statistical_outlier_is_not_a_security_violation():
    report = evaluate_benchmark()
    result = next(item for item in report.results if item.case_id == "benign_latency_outlier")
    assert result.predicted_anomaly is True
    assert result.security_violation is False


def test_explicit_security_violation_is_not_inferred_from_anomaly_score():
    report = evaluate_benchmark()
    result = next(item for item in report.results if item.case_id == "explicit_authz_violation")
    assert result.predicted_anomaly is False
    assert result.security_violation is True


def test_missing_baseline_abstains_and_is_excluded_from_metrics():
    report = evaluate_benchmark()
    result = next(item for item in report.results if item.case_id == "no_baseline")
    assert result.score is None
    assert result.predicted_anomaly is None
    assert report.metrics.unscored == 1
    assert report.metrics.scored == 9


def test_lower_threshold_exposes_false_positive_tradeoff():
    strict = evaluate_benchmark(DEFAULT_CASES, threshold=3.5).metrics
    sensitive = evaluate_benchmark(DEFAULT_CASES, threshold=2.5).metrics
    assert sensitive.false_positive == 1
    assert sensitive.true_positive == strict.true_positive
    assert sensitive.false_positive_rate == 0.2
    assert sensitive.precision == 0.8
    assert sensitive.recall == 1.0
    assert sensitive.accuracy == pytest.approx(8 / 9)


def test_threshold_monotonicity():
    lower = evaluate_benchmark(threshold=2.5)
    higher = evaluate_benchmark(threshold=3.5)
    lower_positive = {r.case_id for r in lower.results if r.predicted_anomaly}
    higher_positive = {r.case_id for r in higher.results if r.predicted_anomaly}
    assert higher_positive <= lower_positive


def test_empty_benchmark_metrics_are_defined():
    metrics = evaluate_benchmark(()).metrics
    assert metrics.scored == 0
    assert metrics.unscored == 0
    assert metrics.precision == metrics.recall == metrics.false_positive_rate == metrics.accuracy == 0.0


@pytest.mark.parametrize("threshold", [0.0, -1.0, math.inf, math.nan])
def test_invalid_threshold_rejected(threshold):
    with pytest.raises(ValueError):
        evaluate_benchmark(threshold=threshold)


def test_duplicate_case_ids_rejected():
    case = BenchmarkCase("duplicate", (1.0, 1.0), 1.0, False, False, "duplicate")
    with pytest.raises(ValueError, match="unique"):
        evaluate_benchmark((case, case))


@pytest.mark.parametrize(
    "baseline,value,label",
    [
        ((), 1.0, False),
        ((1.0,), 1.0, None),
        ((math.inf,), 1.0, True),
        ((1.0,), math.nan, True),
    ],
)
def test_invalid_case_contract_rejected(baseline, value, label):
    with pytest.raises(ValueError):
        BenchmarkCase("invalid", baseline, value, label, False, "invalid")
