# SwarmForge Pro

FastAPI service plus `npsolve`, a self-improving heuristic solver for
NP-hard problems (TSP, Max-Cut, 0/1 Knapsack). Pure stdlib — no numpy,
no external ML deps.

## How the buzzwords map to real algorithms

| Concept | Implementation |
|---|---|
| Superposition / entropy | A probability model over solution components (Cross-Entropy Method / EDA). Sampling "collapses" it into concrete solutions; its Shannon entropy measures convergence and gates exploration. `npsolve/superposition.py` |
| Reinforcement learning | A UCB1 multi-armed bandit learns online which mutation operator (2-opt, or-opt, bit flips, …) yields the most improvement. `npsolve/rl.py` |
| ML / heuristics | Simulated annealing with geometric cooling and Metropolis acceptance refines each sampled solution. `npsolve/anneal.py` |
| Outputs looping back as input data | Each epoch's elite solutions update the probability model and re-seed the next epoch's workers; the bandit's learned policy persists across epochs. `npsolve/orchestrator.py` |
| Chain-of-thought meta-prompting / meta-orchestration | A rule-based meta-controller reflects on every epoch (improvement, entropy, acceptance rate, operator policy), records an explicit observation → diagnosis → action trace, and retunes its own hyperparameters before the next epoch. `npsolve/orchestrator.py` |

What it is **not**: there is no quantum computer and no LLM in the loop.
The reflection step is deterministic rules, and "superposition" is a
probability distribution — that's the honest, working version of the idea.

## Run it

```bash
# CLI demo — prints per-epoch reasoning trace and writes a JSON report
python -m npsolve --problem tsp --size 60 --epochs 8 --seed 42
python -m npsolve --problem maxcut --size 50
python -m npsolve --problem knapsack --size 80

# Tests
python -m pytest tests/ -q

# API
pip install -r requirements.txt
python main.py
curl -X POST localhost:8000/solve -H 'content-type: application/json' \
     -d '{"problem": "tsp", "size": 40, "epochs": 6}'
```

## The self-improvement loop

```
        ┌─────────────────────────────────────────────────┐
        │                                                 │
        ▼                                                 │
  SAMPLE the superposition model ──► REFINE via annealing │
  (+ recycle last epoch's outputs)   (RL bandit picks ops)│
                                          │               │
                                          ▼               │
  REFLECT: chain-of-thought  ◄── FEEDBACK: elites update  │
  meta-controller retunes        the model (outputs ──────┘
  its own hyperparameters        become next inputs)
```

Stopping: early exit when the model entropy has collapsed and no
improvement has occurred for `stall_patience` epochs.
