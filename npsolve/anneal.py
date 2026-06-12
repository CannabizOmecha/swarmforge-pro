"""Simulated annealing worker with RL-driven operator selection.

Each step the UCB1 bandit picks a mutation operator; the proposal is
accepted by the Metropolis criterion. The bandit is rewarded by the
relative improvement, so over time the search concentrates effort on
the operators that actually work for this problem instance.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .rl import UCB1Bandit


@dataclass
class AnnealResult:
    best: list[int]
    best_cost: float
    accepted: int
    proposed: int


def anneal(
    problem,
    start: list[int],
    bandit: UCB1Bandit,
    rng: random.Random,
    steps: int,
    t_start: float,
    t_end: float,
) -> AnnealResult:
    operators = problem.operators()
    current = start
    current_cost = problem.evaluate(current)
    best, best_cost = current, current_cost
    accepted = 0
    scale = max(abs(current_cost), 1e-9)  # normalises rewards and temperature

    for step in range(steps):
        frac = step / max(steps - 1, 1)
        temperature = t_start * (t_end / t_start) ** frac  # geometric cooling

        arm = bandit.select()
        candidate = operators[arm](current, rng)
        cost = problem.evaluate(candidate)
        delta = cost - current_cost

        if delta < 0 or rng.random() < math.exp(-delta / (temperature * scale)):
            current, current_cost = candidate, cost
            accepted += 1
            if cost < best_cost:
                best, best_cost = candidate, cost

        bandit.update(arm, -delta / scale if delta < 0 else 0.0)

    return AnnealResult(best=best, best_cost=best_cost, accepted=accepted, proposed=steps)
