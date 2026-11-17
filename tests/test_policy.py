import pytest

from aegis.policy import (
    POLICY_VERSION,
    SCOPES,
    AuthorizationError,
    Scope,
    authorize,
    validate_scope_registry,
)


def test_python_policy_accepts_only_bounded_local_synthetic_scope():
    scope = authorize("local-synthetic", "execute", 20)
    assert scope.environment == "synthetic-fixtures"
    assert scope.network_enabled is False
    assert scope.max_batch_size == 200
    assert validate_scope_registry()


@pytest.mark.parametrize(
    ("scope_id", "operation", "batch_size"),
    [
        ("production", "execute", 1),
        ("local-synthetic", "deploy", 1),
        ("local-synthetic", "execute", 0),
        ("local-synthetic", "execute", 201),
    ],
)
def test_python_policy_denies_unknown_or_out_of_bounds_requests(
    scope_id, operation, batch_size
):
    with pytest.raises(AuthorizationError):
        authorize(scope_id, operation, batch_size)


def test_scope_registry_is_immutable():
    with pytest.raises(TypeError):
        SCOPES["production"] = Scope(
            scope_id="production",
            environment="production",
            allowed_operations=frozenset({"execute"}),
            max_batch_size=1,
        )


def test_scope_registry_rejects_network_enabled_or_expanded_scopes():
    network_scope = Scope(
        scope_id="local-synthetic",
        environment="synthetic-fixtures",
        allowed_operations=frozenset({"execute"}),
        max_batch_size=10,
        network_enabled=True,
    )
    with pytest.raises(ValueError):
        validate_scope_registry({"local-synthetic": network_scope})

    expanded = {
        "local-synthetic": SCOPES["local-synthetic"],
        "production": Scope(
            scope_id="production",
            environment="production",
            allowed_operations=frozenset({"execute"}),
            max_batch_size=1,
        ),
    }
    with pytest.raises(ValueError):
        validate_scope_registry(expanded)


def test_python_policy_version_is_explicit():
    assert POLICY_VERSION == "1.0.0"
