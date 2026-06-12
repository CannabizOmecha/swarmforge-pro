"""Reinforcement learning for operator selection.

A UCB1 multi-armed bandit treats each mutation operator as an arm.
Reward = 1 when a proposal improved the current solution, scaled by the
relative improvement. The bandit's statistics persist across epochs, so
the orchestrator's feedback loop keeps training the same policy on its
own past outputs.
"""

from __future__ import annotations

import math


class UCB1Bandit:
    def __init__(self, arms: list[str], exploration: float = 1.4):
        self.arms = list(arms)
        self.exploration = exploration
        self.counts = {a: 0 for a in self.arms}
        self.rewards = {a: 0.0 for a in self.arms}

    @property
    def total_pulls(self) -> int:
        return sum(self.counts.values())

    def select(self) -> str:
        for arm in self.arms:  # play every arm once first
            if self.counts[arm] == 0:
                return arm
        log_t = math.log(self.total_pulls)
        return max(
            self.arms,
            key=lambda a: self.rewards[a] / self.counts[a]
            + self.exploration * math.sqrt(log_t / self.counts[a]),
        )

    def update(self, arm: str, reward: float) -> None:
        self.counts[arm] += 1
        self.rewards[arm] += max(0.0, min(1.0, reward))

    def policy(self) -> dict[str, float]:
        """Mean reward per arm — reported in the reasoning trace."""
        return {
            a: (self.rewards[a] / self.counts[a] if self.counts[a] else 0.0)
            for a in self.arms
        }

    def state(self) -> dict:
        return {"counts": dict(self.counts), "rewards": dict(self.rewards)}

    def load_state(self, state: dict) -> None:
        for a in self.arms:
            self.counts[a] = state.get("counts", {}).get(a, 0)
            self.rewards[a] = state.get("rewards", {}).get(a, 0.0)
