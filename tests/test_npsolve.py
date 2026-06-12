import itertools
import random

from npsolve import MetaOrchestrator, OrchestratorConfig, make_problem
from npsolve.problems import Knapsack, TSP
from npsolve.rl import UCB1Bandit
from npsolve.superposition import BitstringModel, TourModel


def small_config(**overrides):
    base = dict(epochs=5, workers=4, steps_per_worker=400, seed=7)
    base.update(overrides)
    return OrchestratorConfig(**base)


def random_baseline(problem, rng, samples=50):
    return min(problem.evaluate(problem.random_solution(rng)) for _ in range(samples))


def test_beats_random_baseline_on_all_problems():
    for name in ("tsp", "maxcut", "knapsack"):
        rng = random.Random(1)
        problem = make_problem(name, 25, rng)
        baseline = random_baseline(problem, rng)
        summary = MetaOrchestrator(problem, small_config()).run()
        assert summary["best_cost"] < baseline, name


def test_tsp_solution_is_valid_permutation():
    rng = random.Random(2)
    problem = TSP.random_instance(20, rng)
    summary = MetaOrchestrator(problem, small_config()).run()
    assert sorted(summary["best_solution"]) == list(range(20))


def test_knapsack_matches_brute_force_on_tiny_instance():
    rng = random.Random(3)
    problem = Knapsack.random_instance(12, rng)
    optimum = min(
        problem.evaluate(list(bits))
        for bits in itertools.product([0, 1], repeat=12)
    )
    summary = MetaOrchestrator(problem, small_config(epochs=8)).run()
    assert abs(summary["best_cost"] - optimum) < 1e-9


def test_knapsack_solution_is_feasible():
    rng = random.Random(4)
    problem = Knapsack.random_instance(30, rng)
    summary = MetaOrchestrator(problem, small_config()).run()
    bits = summary["best_solution"]
    weight = sum(w for w, b in zip(problem.weights, bits) if b)
    assert weight <= problem.capacity


def test_deterministic_given_seed():
    results = []
    for _ in range(2):
        rng = random.Random(5)
        problem = make_problem("tsp", 15, rng)
        results.append(MetaOrchestrator(problem, small_config()).run()["best_cost"])
    assert results[0] == results[1]


def test_chain_of_thought_trace_is_recorded():
    rng = random.Random(6)
    problem = make_problem("maxcut", 15, rng)
    summary = MetaOrchestrator(problem, small_config(epochs=3)).run()
    assert summary["epochs"], "expected at least one epoch report"
    for epoch in summary["epochs"]:
        assert epoch["chain_of_thought"], "every epoch must log its reasoning"
        assert any("Observation" in t for t in epoch["chain_of_thought"])


def test_bandit_prefers_better_arm():
    rng = random.Random(7)
    bandit = UCB1Bandit(["good", "bad"])
    for _ in range(200):
        arm = bandit.select()
        bandit.update(arm, 0.9 if arm == "good" else 0.1)
    policy = bandit.policy()
    assert policy["good"] > policy["bad"]
    assert bandit.counts["good"] > bandit.counts["bad"]


def test_bitstring_model_entropy_drops_after_updates():
    model = BitstringModel(20)
    start = model.entropy()
    assert abs(start - 1.0) < 1e-9  # uniform superposition = max entropy
    elite = [[1] * 20 for _ in range(5)]
    for _ in range(10):
        model.update(elite, lr=0.5)
    assert model.entropy() < start
    model.diversify(1.0)
    assert abs(model.entropy() - 1.0) < 1e-9  # fully re-inflated


def test_tour_model_samples_valid_tours_and_sharpens():
    rng = random.Random(8)
    model = TourModel(10)
    tour = model.sample(rng)
    assert sorted(tour) == list(range(10))
    start = model.entropy()
    model.update([list(range(10))] * 5, lr=0.8)
    assert model.entropy() < start
