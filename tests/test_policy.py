import pytest

from aegis.policy import AuthorizationError, authorize


def test_python_policy_accepts_only_bounded_local_synthetic_scope():
    scope = authorize("local-synthetic", "execute", 20)
    assert scope.environment == "synthetic-fixtures"
    assert scope.network_enabled is False
    assert scope.max_batch_size == 200


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
