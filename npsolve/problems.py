"""NP-hard problem definitions with a shared minimisation interface.

Every problem exposes:
    random_solution(rng)        -> solution
    evaluate(solution)          -> float cost (lower is better)
    operators()                 -> {name: fn(solution, rng) -> new solution}
    solution_kind               -> "permutation" | "bitstring"

Costs are minimised everywhere; maximisation problems negate their
objective so the whole stack only ever minimises.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# Travelling Salesman
# --------------------------------------------------------------------------

@dataclass
class TSP:
    cities: list[tuple[float, float]]
    solution_kind: str = field(default="permutation", init=False)

    @classmethod
    def random_instance(cls, n: int, rng: random.Random) -> "TSP":
        return cls(cities=[(rng.random(), rng.random()) for _ in range(n)])

    @property
    def size(self) -> int:
        return len(self.cities)

    def distance(self, a: int, b: int) -> float:
        (x1, y1), (x2, y2) = self.cities[a], self.cities[b]
        return math.hypot(x1 - x2, y1 - y2)

    def random_solution(self, rng: random.Random) -> list[int]:
        tour = list(range(self.size))
        rng.shuffle(tour)
        return tour

    def evaluate(self, tour: list[int]) -> float:
        return sum(
            self.distance(tour[i], tour[(i + 1) % len(tour)])
            for i in range(len(tour))
        )

    # -- mutation operators (the RL bandit chooses among these) -----------

    @staticmethod
    def _two_opt(tour: list[int], rng: random.Random) -> list[int]:
        i, j = sorted(rng.sample(range(len(tour)), 2))
        return tour[:i] + tour[i : j + 1][::-1] + tour[j + 1 :]

    @staticmethod
    def _swap(tour: list[int], rng: random.Random) -> list[int]:
        i, j = rng.sample(range(len(tour)), 2)
        out = tour[:]
        out[i], out[j] = out[j], out[i]
        return out

    @staticmethod
    def _or_opt(tour: list[int], rng: random.Random) -> list[int]:
        n = len(tour)
        seg = rng.randint(1, min(3, n - 1))
        i = rng.randrange(n - seg)
        chunk = tour[i : i + seg]
        rest = tour[:i] + tour[i + seg :]
        k = rng.randrange(len(rest) + 1)
        return rest[:k] + chunk + rest[k:]

    def operators(self):
        return {"two_opt": self._two_opt, "swap": self._swap, "or_opt": self._or_opt}


# --------------------------------------------------------------------------
# Max-Cut
# --------------------------------------------------------------------------

@dataclass
class MaxCut:
    n: int
    edges: list[tuple[int, int, float]]  # (u, v, weight)
    solution_kind: str = field(default="bitstring", init=False)

    @classmethod
    def random_instance(cls, n: int, rng: random.Random, density: float = 0.3) -> "MaxCut":
        edges = [
            (u, v, rng.uniform(0.1, 1.0))
            for u in range(n)
            for v in range(u + 1, n)
            if rng.random() < density
        ]
        return cls(n=n, edges=edges)

    @property
    def size(self) -> int:
        return self.n

    def random_solution(self, rng: random.Random) -> list[int]:
        return [rng.randint(0, 1) for _ in range(self.n)]

    def evaluate(self, bits: list[int]) -> float:
        cut = sum(w for u, v, w in self.edges if bits[u] != bits[v])
        return -cut  # maximise cut == minimise negative cut

    @staticmethod
    def _flip_one(bits: list[int], rng: random.Random) -> list[int]:
        out = bits[:]
        i = rng.randrange(len(out))
        out[i] ^= 1
        return out

    @staticmethod
    def _flip_few(bits: list[int], rng: random.Random) -> list[int]:
        out = bits[:]
        for i in rng.sample(range(len(out)), min(3, len(out))):
            out[i] ^= 1
        return out

    def operators(self):
        return {"flip_one": self._flip_one, "flip_few": self._flip_few}


# --------------------------------------------------------------------------
# 0/1 Knapsack
# --------------------------------------------------------------------------

@dataclass
class Knapsack:
    values: list[float]
    weights: list[float]
    capacity: float
    solution_kind: str = field(default="bitstring", init=False)

    @classmethod
    def random_instance(cls, n: int, rng: random.Random) -> "Knapsack":
        values = [rng.uniform(1, 100) for _ in range(n)]
        weights = [rng.uniform(1, 50) for _ in range(n)]
        return cls(values=values, weights=weights, capacity=0.4 * sum(weights))

    @property
    def size(self) -> int:
        return len(self.values)

    def _repair(self, bits: list[int]) -> list[int]:
        """Drop worst value/weight items until the knapsack fits."""
        out = bits[:]
        weight = sum(w for w, b in zip(self.weights, out) if b)
        while weight > self.capacity:
            chosen = [i for i, b in enumerate(out) if b]
            worst = min(chosen, key=lambda i: self.values[i] / self.weights[i])
            out[worst] = 0
            weight -= self.weights[worst]
        return out

    def random_solution(self, rng: random.Random) -> list[int]:
        return self._repair([rng.randint(0, 1) for _ in range(self.size)])

    def evaluate(self, bits: list[int]) -> float:
        weight = sum(w for w, b in zip(self.weights, bits) if b)
        value = sum(v for v, b in zip(self.values, bits) if b)
        if weight > self.capacity:  # infeasible: heavy linear penalty
            value -= 10.0 * max(self.values) * (weight - self.capacity)
        return -value

    def _flip_repair(self, bits: list[int], rng: random.Random) -> list[int]:
        out = bits[:]
        out[rng.randrange(len(out))] ^= 1
        return self._repair(out)

    def _add_greedy(self, bits: list[int], rng: random.Random) -> list[int]:
        out = bits[:]
        absent = [i for i, b in enumerate(out) if not b]
        if absent:
            out[rng.choice(absent)] = 1
        return self._repair(out)

    def operators(self):
        return {"flip_repair": self._flip_repair, "add_greedy": self._add_greedy}


# --------------------------------------------------------------------------

def make_problem(name: str, size: int, rng: random.Random):
    name = name.lower()
    if name == "tsp":
        return TSP.random_instance(size, rng)
    if name in ("maxcut", "max-cut"):
        return MaxCut.random_instance(size, rng)
    if name == "knapsack":
        return Knapsack.random_instance(size, rng)
    raise ValueError(f"unknown problem {name!r}; expected tsp, maxcut or knapsack")
