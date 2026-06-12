"""CLI demo:  python -m npsolve --problem tsp --size 60 --epochs 8 --seed 42

Writes the full run summary (including the chain-of-thought trace and
bandit state) to a JSON file that can be inspected or fed onward.
"""

from __future__ import annotations

import argparse
import json
import random

from .orchestrator import MetaOrchestrator, OrchestratorConfig
from .problems import make_problem


def main() -> None:
    parser = argparse.ArgumentParser(description="Self-improving NP-hard heuristic solver")
    parser.add_argument("--problem", default="tsp", choices=["tsp", "maxcut", "knapsack"])
    parser.add_argument("--size", type=int, default=60)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=None, help="path for the JSON run report")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    problem = make_problem(args.problem, args.size, rng)
    config = OrchestratorConfig(
        epochs=args.epochs, workers=args.workers,
        steps_per_worker=args.steps, seed=args.seed,
    )

    baseline = min(problem.evaluate(problem.random_solution(rng)) for _ in range(50))
    print(f"{args.problem} n={args.size} | best of 50 random solutions: {baseline:.4f}\n")

    orchestrator = MetaOrchestrator(problem, config)
    summary = orchestrator.run()

    for epoch in summary["epochs"]:
        print(
            f"epoch {epoch['epoch']}: cost={epoch['best_cost']:.4f} "
            f"entropy={epoch['entropy']:.3f} accept={epoch['acceptance_rate']:.2f}"
        )
        for thought in epoch["chain_of_thought"]:
            print(f"    · {thought}")

    gain = (baseline - summary["best_cost"]) / abs(baseline) * 100 if baseline else 0.0
    print(
        f"\nfinal cost: {summary['best_cost']:.4f} "
        f"({gain:.1f}% better than random baseline) "
        f"in {summary['elapsed_sec']}s / {summary['epochs_run']} epochs"
    )
    print(f"learned operator policy: {summary['epochs'][-1]['bandit_policy']}")

    out = args.out or f"npsolve_{args.problem}_{args.size}.json"
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"full report written to {out}")


if __name__ == "__main__":
    main()
