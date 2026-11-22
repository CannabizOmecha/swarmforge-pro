# GitHub branch protection baseline

## Scope

Protect both `main` (the repository default branch) and `aegis-moe-foundation` (the active engineering branch). Use GitHub repository rulesets or classic branch protection. Apply the same baseline to both branches.

## Required settings

| Setting | Required value | Reason |
|---|---|---|
| Require a pull request before merging | Enabled | Prevent direct-to-branch changes |
| Required approving reviews | 1 | Independent human review |
| Dismiss stale approvals on new commits | Enabled | Approval must cover the current diff |
| Require review from Code Owners | Not enabled until an independent CODEOWNERS team/person is configured | Avoid false assurance from self-ownership |
| Require conversation resolution | Enabled | Review findings must be closed |
| Require status checks before merging | Enabled | CI must pass before merge |
| Required status check | `test` | The single CI job runs tests, compile, lint, schemas, policy manifest, and OPA/Rego |
| Require branches to be up to date | Enabled | Test the proposed merge against current base |
| Require linear history | Optional; not required by this baseline | Not necessary for safety gate |
| Include administrators / do not allow bypass | Enabled | Rules apply to repository administrators |
| Allow force pushes | Disabled | Preserve branch history |
| Allow branch deletion | Disabled | Preserve protected refs |

Do not add a required check name until it has been observed on a completed PR check suite. The current workflow job ID/name is `test`; verify the exact check-run name in GitHub before selecting it in the ruleset UI.

## Required CI contract

The workflow at `.github/workflows/ci.yml` runs for pull requests and pushes. The required `test` job includes:

- pytest
- Python compileall
- Ruff
- JSON Schema validation
- immutable policy-manifest verification
- pinned OPA binary digest verification
- Rego formatting, compilation, and policy tests

A green push workflow on a topic branch is not a substitute for a successful required check on the pull request's latest head SHA.

## Reviewer independence

At least one approving reviewer must be different from the pull-request author. Do not use self-approval, a bot identity controlled by the author, or an administrator bypass as independent review. If no independent reviewer is available, leave the PR unmerged and arrange an authorized second reviewer.

## Activation and verification

This repository currently has no rulesets returned by the GitHub API. The branch-protection read endpoint returned HTTP 403 (`Resource not accessible by integration`). The connected GitHub integration exposes read operations but no branch-protection/ruleset write operation. Therefore this document is a configuration specification, not proof that GitHub is enforcing it.

A repository administrator must enable the settings above in GitHub repository Settings → Rules → Rulesets (or Settings → Branches → Branch protection rules). After activation:

1. Read back the ruleset/branch-protection configuration.
2. Open a test pull request.
3. Verify merge is blocked with no approval.
4. Verify merge remains blocked when `test` is pending or failing.
5. Verify an approval from a person other than the author plus a successful current-head `test` check permits merge.
6. Verify stale approval is dismissed after a new commit.
7. Verify administrators cannot bypass the rules.

Do not claim enforcement until the read-back and negative/positive tests have been recorded. Record the ruleset ID, target branches, required check name, reviewer identity/team, verification PR, and date here.

## Activation record

- Status: **PENDING ADMINISTRATOR ACTIVATION**
- Ruleset ID: not yet available
- Protected branches: target `main`, `aegis-moe-foundation`
- Required check: `test` (must be confirmed from a PR check run)
- Independent reviewer: not yet designated
- Negative/positive enforcement test: not run
