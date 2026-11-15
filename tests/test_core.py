from aegis.baseline import is_anomalous, mad, robust_anomaly_score
from aegis.engine import canonical_hash, execute_synthetic_run
from aegis.policy import AuthorizationError, authorize
from aegis.privacy import minimize_attributes, redact_text


def test_mad_and_robust_score():
    assert mad([1, 2, 3, 4, 100]) == 1
    assert robust_anomaly_score([10, 10, 10], 10) == 0
    assert is_anomalous([10, 10, 10], 99)


def test_policy_fails_closed():
    authorize("local-synthetic", "execute", 2)
    for scope, operation, count in [
        ("unknown", "execute", 1),
        ("local-synthetic", "execute", 201),
        ("local-synthetic", "publish", 1),
    ]:
        try:
            authorize(scope, operation, count)
            assert False, "unauthorized request must be denied"
        except AuthorizationError:
            pass


def test_privacy_minimization():
    assert "[REDACTED_EMAIL]" in redact_text("contact a.person@example.com")
    clean = minimize_attributes(
        {"operation": "read", "email": "a.person@example.com", "status_code": 200}
    )
    assert "email" not in clean
    assert clean["operation"] == "read"


def test_synthetic_run_produces_reproducible_evidence():
    run, findings, evidence = execute_synthetic_run("local-synthetic", 10, 7)
    assert run.status == "completed"
    assert len(run.observations) == 10
    assert len(findings) == 1
    assert findings[0].state.value == "validated"
    assert len(evidence[0].payload_sha256) == 64
    assert canonical_hash(evidence[0].manifest) == evidence[0].payload_sha256


def test_remote_scope_is_not_supported():
    try:
        execute_synthetic_run("production", 5, 1)
        assert False, "remote scope must be denied"
    except AuthorizationError:
        pass
