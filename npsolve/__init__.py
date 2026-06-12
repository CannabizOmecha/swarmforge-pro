"""npsolve: self-improving heuristic solver for NP-hard problems.

Architecture (every term maps to a concrete algorithm, no magic):

- Problems        : TSP, Max-Cut, 0/1 Knapsack (problems.py)
- "Superposition" : a probabilistic model over solution components
                    (Estimation-of-Distribution / Cross-Entropy Method).
                    Sampling the model "collapses" it into concrete
                    solutions; its Shannon entropy measures how far the
                    search has converged (superposition.py)
- RL              : a UCB1 multi-armed bandit that learns online which
                    mutation operator yields the most improvement (rl.py)
- Annealing       : Metropolis acceptance with an adaptive temperature
                    schedule drives local refinement (anneal.py)
- Meta-orchestration / self-improvement loop:
                    each epoch's *output* (elite solutions + run stats)
                    becomes the next epoch's *input data*. A rule-based
                    meta-controller reflects on the stats, records an
                    explicit chain-of-thought trace, and retunes its own
                    hyperparameters before the next epoch (orchestrator.py)
"""

from .problems import TSP, MaxCut, Knapsack, make_problem
from .orchestrator import MetaOrchestrator, OrchestratorConfig

__all__ = [
    "TSP",
    "MaxCut",
    "Knapsack",
    "make_problem",
    "MetaOrchestrator",
    "OrchestratorConfig",
]
