from statistics import median
from typing import Iterable


def mad(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        return 0.0
    center = median(items)
    return median([abs(x - center) for x in items])


def robust_anomaly_score(values: list[float], value: float) -> float:
    """Return a non-negative robust z-like score; zero when dispersion is zero and value matches."""
    if not values:
        return 0.0
    center = median(values)
    dispersion = mad(values)
    if dispersion == 0:
        return 0.0 if value == center else 10.0
    return abs(value - center) / (1.4826 * dispersion)


def is_anomalous(values: list[float], value: float, threshold: float = 3.5) -> bool:
    return robust_anomaly_score(values, value) >= threshold
