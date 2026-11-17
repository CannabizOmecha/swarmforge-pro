from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aegis.policy import POLICY_VERSION, validate_scope_registry


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "spec" / "policy-manifest.json"


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    relative_path = Path(manifest["policy_path"])
    policy_path = (ROOT / relative_path).resolve()
    if ROOT not in policy_path.parents:
        raise SystemExit("Policy manifest path escapes the repository root.")

    content = policy_path.read_bytes()
    actual_digest = hashlib.sha256(content).hexdigest()
    if actual_digest != manifest["policy_sha256"]:
        raise SystemExit(
            f"Policy digest mismatch: expected {manifest['policy_sha256']}, got {actual_digest}"
        )

    text = content.decode("utf-8")
    version_marker = f'policy_version := "{manifest["policy_version"]}"'
    if version_marker not in text or POLICY_VERSION != manifest["policy_version"]:
        raise SystemExit("Python and Rego policy versions do not match the manifest.")

    validate_scope_registry()
    print(
        f"Policy manifest valid: {manifest['policy_id']} "
        f"v{manifest['policy_version']} sha256={actual_digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
