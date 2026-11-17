package aegis.authorization

default allow := false

# The policy accepts exactly the four fields emitted by the local policy adapter.
# Extra fields are rejected so a caller cannot smuggle target or credential data.
allow if {
    count(object.keys(input)) == 4
    input.scope_id == "local-synthetic"
    input.operation in {"generate", "execute", "observe", "validate", "evidence"}
    input.batch_size >= 1
    input.batch_size <= 200
    input.network_enabled == false
}

deny_reason := "unknown_or_unauthorized_scope" if {
    not allow
}
