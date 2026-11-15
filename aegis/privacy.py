import re
from typing import Any

EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?1[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]?\d{4}(?!\w)")
TOKEN = re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+")


def redact_text(value: str) -> str:
    value = EMAIL.sub("[REDACTED_EMAIL]", value)
    value = PHONE.sub("[REDACTED_PHONE]", value)
    return TOKEN.sub("[REDACTED_SECRET]", value)


def minimize_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    allowed = {"status_code", "operation", "latency_bucket", "property_id", "outcome", "service_version"}
    clean: dict[str, Any] = {}
    for key, value in attributes.items():
        if key not in allowed:
            continue
        clean[key] = redact_text(value) if isinstance(value, str) else value
    return clean
