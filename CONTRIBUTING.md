# Contributing to AEGIS MoE

## Protected-branch workflow

All changes intended for `main` or `aegis-moe-foundation` must be proposed through a pull request. Do not treat a successful push-triggered workflow as permission to bypass review.

A merge is permitted only when all of the following are true:

1. The pull request has at least one approving review from a person other than its author.
2. The author has not approved their own pull request.
3. All requested changes and review conversations are resolved.
4. The required GitHub Actions check named `test` has succeeded for the latest pull-request head commit.
5. The pull request is up to date with its base branch.
6. The diff preserves the repository's safety invariants and is within the documented local-synthetic scope.

Do not merge with failing, pending, skipped, or stale required checks. Do not use an administrator bypass to avoid review or CI.

## Engineering requirements

- Make the smallest change that satisfies a repository-backed requirement.
- Add deterministic tests for new behavior and regression tests for corrected defects.
- Keep telemetry bounded and privacy-safe. Never use user-controlled or high-cardinality values as metric labels.
- Preserve fail-closed authorization and validation behavior.
- Do not add remote target execution, network scanning, exploitation, credential harvesting, stealth, persistence, or external disclosure.
- Do not claim production readiness without independent evidence and completion of the release gate in `docs/ACCEPTANCE.md`.
- Update relevant acceptance evidence and documentation in the same change.

## Pull request procedure

1. Create a focused topic branch from the intended base.
2. Implement and test locally.
3. Open a pull request and complete the safety checklist.
4. Obtain an independent review.
5. Wait for the required `test` check on the latest PR head SHA.
6. Resolve all conversations, update the branch if required, and use the repository's permitted merge method.

These contribution requirements become technically enforceable only after the GitHub branch-protection settings documented in `docs/BRANCH_PROTECTION.md` are enabled and verified.
