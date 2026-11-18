# Offline Anomaly Benchmark

## Purpose

This benchmark is a deterministic calibration smoke test for the robust latency anomaly score. It uses only synthetic values and requires no API, provider, network, credentials, or stored user telemetry.

It does **not** estimate security-vulnerability detection performance. A statistical anomaly may be benign; an explicit security-property violation may occur with a nominal score. The security validator remains a separate gate.

## Run

```python
from aegis.benchmark import DEFAULT_CASES, evaluate_benchmark

report = evaluate_benchmark(DEFAULT_CASES, threshold=3.5)
print(report.metrics)
```

The default fixture includes nominal observations, benign variation, statistical outliers, a synthetic latency regression, zero-dispersion baselines, an explicit authorization-property violation with nominal latency, and one missing-baseline abstention.

## Default expected results

At threshold 3.5:
- TP 4, FP 0, TN 5, FN 0.
- 9 scored cases and 1 unscored case.
- Precision 1.0, recall 1.0, false-positive rate 0.0, accuracy 1.0.

At threshold 2.5, the benign upper-variation case becomes a false positive:
- TP 4, FP 1, TN 4, FN 0.
- Precision 0.8, recall 1.0, false-positive rate 0.2, accuracy 8/9.

These figures describe only this tiny, hand-authored fixture. They are not evidence of production calibration, generalization, or vulnerability-detection accuracy. A larger held-out benchmark with distributions and independent ground-truth review is required before changing thresholds or using anomaly scores for automated security decisions.
