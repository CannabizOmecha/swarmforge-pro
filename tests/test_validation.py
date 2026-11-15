import pytest
from jsonschema.exceptions import ValidationError

from aegis.engine import execute_synthetic_run
from aegis.validation import validate_event, validate_evidence_manifest


def test_generated_events_and_evidence_meet_versioned_schemas():
    run, _, evidence = execute_synthetic_run("local-synthetic", 10, 19)
    assert run.observations
    for observation in run.observations:
        validate_event(observation)
    assert len(evidence) == 1
    validate_evidence_manifest(evidence[0].manifest)


def test_event_schema_rejects_unapproved_fields():
    run, _, _ = execute_synthetic_run("local-synthetic", 2, 19)
    event = run.observations[0].model_dump(mode="json")
    event["email"] = "should-not-be-collected@example.invalid"
    with pytest.raises(ValidationError):
        validate_event(event)


def test_evidence_schema_rejects_invalid_scope_and_uuid():
    _, _, evidence = execute_synthetic_run("local-synthetic", 10, 19)
    manifest = dict(evidence[0].manifest)
    manifest["scope_id"] = "production"
    with pytest.raises(ValidationError):
        validate_evidence_manifest(manifest)

    manifest = dict(evidence[0].manifest)
    manifest["run_id"] = "not-a-uuid"
    with pytest.raises(ValidationError):
        validate_evidence_manifest(manifest)
