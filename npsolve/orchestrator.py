"""Meta-orchestrator: the self-improvement loop.

Each epoch:
  1. SAMPLE   — collapse the superposition model into K start solutions
               (plus the best-so-far, so outputs literally re-enter as
               input data).
  2. REFINE   — run an annealing worker on each start; the shared UCB1
               bandit keeps learning which operators pay off.
  3. FEEDBACK — the epoch's elite outputs update the superposition model
               (cross-entropy update) and are carried into the next
               epoch's inputs.
  4. REFLECT  — a rule-based meta-controller examines the epoch stats
               (improvement, acceptance rate, model entropy, bandit
               policy), writes an explicit chain-of-thought trace, and
               retunes its own hyperparameters (temperature, workers,
               diversity injection) for the next epoch.

The reflection step is deterministic rules, not an LLM — but the trace
makes every meta-decision auditable, and the loop is genuinely
self-referential: epoch N+1 consumes nothing except epoch N's outputs.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from .anneal import anneal
from .rl import UCB1Bandit
from .superposition import model_for


@dataclass
class OrchestratorConfig:
    epochs: int = 8
    workers: int = 8
    steps_per_worker: int = 1500
    elite_fraction: float = 0.3
    model_lr: float = 0.3
    t_start: float = 0.05
    t_end: float = 0.001
    seed: int = 0
    stall_patience: int = 3  # epochs without improvement before stopping


@dataclass
class EpochReport:
    epoch: int
    best_cost: float
    improvement: float
    entropy: float
    acceptance_rate: float
    bandit_policy: dict[str, float]
    reflections: list[str] = field(default_factory=list)


class MetaOrchestrator:
    def __init__(self, problem, config: OrchestratorConfig | None = None):
        self.problem = problem
        self.config = config or OrchestratorConfig()
        self.rng = random.Random(self.config.seed)
        self.model = model_for(problem)
        self.bandit = UCB1Bandit(list(problem.operators().keys()))
        self.best: list[int] | None = None
        self.best_cost = float("inf")
        self.history: list[EpochReport] = []
        self._elites: list[list[int]] = []  # last epoch's outputs -> next inputs
        self._stalled = 0

    # -- the loop ----------------------------------------------------------

    def run(self) -> dict:
        started = time.monotonic()
        for epoch in range(self.config.epochs):
            report = self._run_epoch(epoch)
            self._reflect(report)
            self.history.append(report)
            if self._stalled >= self.config.stall_patience:
                report.reflections.append(
                    f"No improvement for {self._stalled} epochs at entropy "
                    f"{report.entropy:.3f}; search has converged — stopping early."
                )
                break
        return self.summary(elapsed=time.monotonic() - started)

    def _run_epoch(self, epoch: int) -> EpochReport:
        cfg = self.config
        prev_best = self.best_cost

        # 1. SAMPLE: model samples + recycled outputs from the last epoch
        starts: list[list[int]] = []
        if self.best is not None:
            starts.append(self.best)
        starts.extend(self._elites[: cfg.workers // 2])
        while len(starts) < cfg.workers:
            starts.append(self.model.sample(self.rng))

        # 2. REFINE
        results = [
            anneal(
                self.problem, s, self.bandit, self.rng,
                steps=cfg.steps_per_worker, t_start=cfg.t_start, t_end=cfg.t_end,
            )
            for s in starts
        ]
        results.sort(key=lambda r: r.best_cost)
        if results[0].best_cost < self.best_cost:
            self.best, self.best_cost = results[0].best, results[0].best_cost

        # 3. FEEDBACK: outputs become next epoch's input data
        n_elite = max(1, int(cfg.elite_fraction * len(results)))
        self._elites = [r.best for r in results[:n_elite]]
        self.model.update(self._elites, lr=cfg.model_lr)

        accepted = sum(r.accepted for r in results)
        proposed = sum(r.proposed for r in results)
        return EpochReport(
            epoch=epoch,
            best_cost=self.best_cost,
            improvement=prev_best - self.best_cost if prev_best != float("inf") else 0.0,
            entropy=self.model.entropy(),
            acceptance_rate=accepted / max(proposed, 1),
            bandit_policy=self.bandit.policy(),
        )

    # -- 4. REFLECT: chain-of-thought meta-control --------------------------

    def _reflect(self, report: EpochReport) -> None:
        cfg = self.config
        think = report.reflections.append
        improved = report.improvement > 1e-9 or report.epoch == 0

        best_op = max(report.bandit_policy, key=report.bandit_policy.get)
        think(
            f"Observation: best cost {report.best_cost:.4f}, model entropy "
            f"{report.entropy:.3f}, acceptance {report.acceptance_rate:.2f}, "
            f"most rewarding operator '{best_op}'."
        )

        if improved:
            self._stalled = 0
            cfg.t_start *= 0.85
            think(
                "Diagnosis: still improving. Action: keep the current strategy "
                f"and cool the start temperature to {cfg.t_start:.4f} to "
                "sharpen exploitation."
            )
        else:
            self._stalled += 1
            if report.entropy < 0.35:
                self.model.diversify(0.5)
                cfg.t_start = min(cfg.t_start * 2.5, 0.2)
                think(
                    "Diagnosis: stalled AND the superposition has nearly "
                    "collapsed (low entropy) — the search is stuck in a basin. "
                    "Action: re-inflate the model toward uniform and reheat to "
                    f"t_start={cfg.t_start:.4f} to force exploration."
                )
            else:
                cfg.elite_fraction = max(0.15, cfg.elite_fraction * 0.8)
                cfg.steps_per_worker = int(cfg.steps_per_worker * 1.3)
                think(
                    "Diagnosis: stalled but entropy is still high — workers "
                    "are not refining long enough. Action: tighten the elite "
                    f"set to {cfg.elite_fraction:.2f} and extend refinement to "
                    f"{cfg.steps_per_worker} steps per worker."
                )

        if report.acceptance_rate > 0.6:
            cfg.t_start *= 0.7
            think(
                "Diagnosis: acceptance rate is too permissive (random-walk "
                f"regime). Action: cool t_start to {cfg.t_start:.4f}."
            )

    # -- reporting -----------------------------------------------------------

    def summary(self, elapsed: float = 0.0) -> dict:
        return {
            "problem": type(self.problem).__name__,
            "size": self.problem.size,
            "best_cost": self.best_cost,
            "best_solution": self.best,
            "epochs_run": len(self.history),
            "elapsed_sec": round(elapsed, 3),
            "bandit_state": self.bandit.state(),
            "final_entropy": self.model.entropy(),
            "epochs": [
                {
                    "epoch": r.epoch,
                    "best_cost": r.best_cost,
                    "improvement": r.improvement,
                    "entropy": round(r.entropy, 4),
                    "acceptance_rate": round(r.acceptance_rate, 4),
                    "bandit_policy": {k: round(v, 4) for k, v in r.bandit_policy.items()},
                    "chain_of_thought": r.reflections,
                }
                for r in self.history
            ],
        }
