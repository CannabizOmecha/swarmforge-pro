package aegis.authorization

default allow := false

# This policy deliberately authorizes only the synthetic local fixture.
allow if {
  input.scope_id == "local-synthetic"
  input.operation in {"generate", "execute", "observe", "validate", "evidence"}
  input.batch_size >= 1
  input.batch_size <= 200
  input.network_enabled == false
}

deny_reason := "unknown_or_unauthorized_scope" if {
  not allow
}
