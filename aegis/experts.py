from dataclasses import dataclass


@dataclass(frozen=True)
class Expert:
    name: str
    specialties: tuple[str, ...]
    mode: str = "deterministic"


EXPERTS = (
    Expert("supervisor", ("orchestration", "recovery")),
    Expert("test_generator", ("property_tests", "boundaries")),
    Expert("sandbox", ("isolation", "fixtures")),
    Expert("privacy", ("schema", "redaction")),
    Expert("statistics", ("baseline", "drift")),
    Expert("anomaly", ("scoring", "correlation")),
    Expert("security_validator", ("invariants", "validation")),
    Expert("reproduction", ("replay", "minimization")),
    Expert("evidence", ("provenance", "integrity")),
    Expert("quality", ("regression", "evaluation")),
    Expert("optimizer", ("efficiency", "routing")),
    Expert("governance", ("authorization", "policy")),
)


def route(task: str) -> list[str]:
    routes = {
        "run": ["governance", "test_generator", "sandbox", "privacy", "statistics", "anomaly", "security_validator", "evidence", "quality"],
        "validate": ["security_validator", "reproduction", "evidence"],
        "evaluate": ["statistics", "anomaly", "quality", "optimizer"],
    }
    return routes.get(task, ["supervisor", "governance"])
