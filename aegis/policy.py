from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Mapping

POLICY_VERSION = "1.0.0"
ALLOWED_OPERATIONS = frozenset({"generate", "execute", "observe", "validate", "evidence"})


@dataclass(frozen=True)
class Scope:
    scope_id: str
    environment: str
    allowed_operations: frozenset[str]
    max_batch_size: int
    network_enabled: bool = False


SCOPES: Mapping[str, Scope] = MappingProxyType(
    {
        "local-synthetic": Scope(
            scope_id="local-synthetic",
            environment="synthetic-fixtures",
            allowed_operations=ALLOWED_OPERATIONS,
            max_batch_size=200,
            network_enabled=False,
        )
    }
)


class AuthorizationError(PermissionError):
    pass


def validate_scope_registry(scopes: Mapping[str, Scope] | None = None) -> bool:
    registry = SCOPES if scopes is None else scopes
    if set(registry) != {"local-synthetic"}:
        raise ValueError("Scope registry must contain only local-synthetic.")
    for key, scope in registry.items():
        if key != scope.scope_id:
            raise ValueError("Scope registry key does not match its scope identifier.")
        if scope.environment != "synthetic-fixtures":
            raise ValueError("Only the synthetic fixture environment is supported.")
        if scope.network_enabled:
            raise ValueError("Network-enabled scopes are prohibited.")
        if not scope.allowed_operations or not scope.allowed_operations.issubset(
            ALLOWED_OPERATIONS
        ):
            raise ValueError("Scope contains an unsupported operation.")
        if scope.max_batch_size < 1 or scope.max_batch_size > 200:
            raise ValueError("Scope batch budget is outside the policy envelope.")
    return True


validate_scope_registry()


def authorize(scope_id: str, operation: str, requested_batch: int = 1) -> Scope:
    scope = SCOPES.get(scope_id)
    if scope is None:
        raise AuthorizationError("Unknown scope; execution denied.")
    if operation not in scope.allowed_operations:
        raise AuthorizationError("Operation is not authorized for this scope.")
    if requested_batch < 1 or requested_batch > scope.max_batch_size:
        raise AuthorizationError("Requested batch exceeds the scope budget.")
    if scope.network_enabled:
        raise AuthorizationError("This MVP does not permit network-enabled scopes.")
    return scope
