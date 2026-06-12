"""'Superposition' models: probability distributions over solution space.

This is the Estimation-of-Distribution / Cross-Entropy Method made
literal: instead of holding one solution, we hold a distribution over
solution components (a weighted superposition of all candidate
solutions). Sampling collapses it into a concrete solution; updating it
from elite outputs sharpens it; its Shannon entropy tells the
orchestrator how converged or diverse the search currently is.

- BitstringModel : independent Bernoulli marginal per bit.
- TourModel      : edge-frequency matrix over city successors.
"""

from __future__ import annotations

import math
import random


def _binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


class BitstringModel:
    def __init__(self, n: int, clamp: float = 0.05):
        self.n = n
        self.clamp = clamp
        self.p = [0.5] * n  # maximum-entropy start: uniform superposition

    def sample(self, rng: random.Random) -> list[int]:
        return [1 if rng.random() < pi else 0 for pi in self.p]

    def update(self, elites: list[list[int]], lr: float) -> None:
        if not elites:
            return
        for i in range(self.n):
            freq = sum(e[i] for e in elites) / len(elites)
            pi = (1 - lr) * self.p[i] + lr * freq
            self.p[i] = min(1 - self.clamp, max(self.clamp, pi))

    def entropy(self) -> float:
        """Mean per-bit entropy, normalised to [0, 1]."""
        return sum(_binary_entropy(pi) for pi in self.p) / self.n

    def diversify(self, amount: float) -> None:
        """Blend back toward uniform — re-inflate the superposition."""
        self.p = [(1 - amount) * pi + amount * 0.5 for pi in self.p]


class TourModel:
    """Edge-frequency model over (city -> next city) transitions."""

    def __init__(self, n: int, floor: float = 0.01):
        self.n = n
        self.floor = floor
        self.w = [[1.0] * n for _ in range(n)]  # uniform pheromone-style weights

    def sample(self, rng: random.Random) -> list[int]:
        start = rng.randrange(self.n)
        tour, visited = [start], {start}
        while len(tour) < self.n:
            cur = tour[-1]
            candidates = [c for c in range(self.n) if c not in visited]
            weights = [self.w[cur][c] for c in candidates]
            tour.append(rng.choices(candidates, weights=weights)[0])
            visited.add(tour[-1])
        return tour

    def update(self, elites: list[list[int]], lr: float) -> None:
        if not elites:
            return
        freq = [[0.0] * self.n for _ in range(self.n)]
        for tour in elites:
            for i in range(self.n):
                freq[tour[i]][tour[(i + 1) % self.n]] += 1.0 / len(elites)
        for a in range(self.n):
            for b in range(self.n):
                w = (1 - lr) * self.w[a][b] + lr * freq[a][b] * self.n
                self.w[a][b] = max(self.floor, w)

    def entropy(self) -> float:
        """Mean normalised entropy of each city's successor distribution."""
        total = 0.0
        for a in range(self.n):
            row = self.w[a]
            s = sum(row)
            h = -sum((v / s) * math.log2(v / s) for v in row if v > 0)
            total += h / math.log2(self.n)
        return total / self.n

    def diversify(self, amount: float) -> None:
        mean = sum(sum(r) for r in self.w) / (self.n * self.n)
        for a in range(self.n):
            for b in range(self.n):
                self.w[a][b] = (1 - amount) * self.w[a][b] + amount * mean


def model_for(problem) -> BitstringModel | TourModel:
    if problem.solution_kind == "permutation":
        return TourModel(problem.size)
    return BitstringModel(problem.size)
