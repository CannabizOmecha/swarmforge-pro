from dataclasses import dataclass


@dataclass(frozen=True)
class Scope:
    scope_id: str
    environment: str
    allowed_operations: frozenset[str]
    max_batch_size: int
    network_enabled: bool = False


SCOPES = {
    "local-synthetic": Scope(
        scope_id="local-synthetic",
        environment="synthetic-fixtures",
        allowed_operations=frozenset({"generate", "execute", "observe", "validate", "evidence"}),
        max_batch_size=200,
        network_enabled=False,
    )
}


class AuthorizationError(PermissionError):
    pass


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
