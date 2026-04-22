# Evaluation: `alaviron/tableau-skills`

Date: 2026-04-17
Status: Partial evaluation only
Source inspected: direct web endpoint and Git endpoint

## Repository overview and operating model

The upstream repository could not be inspected from this session. The web endpoint redirected to enterprise SSO, and the Git endpoint denied anonymous access. That means the repository exists, but its contents were not available for asset-by-asset inspection.

## Inventory by folder and asset type

Complete inventory: unavailable.

Accessible evidence:
- Web access redirects to enterprise authentication.
- Git access returns anonymous access denied.

No file tree, README, scripts, prompts, or skills were retrievable from the current session.

## Mapping to this repo's current structure

This workspace already has a stable comparison baseline:
- `skills/` for repeated operational workflows.
- `playbooks/` for step-by-step operator documentation.
- `prompts/` for reusable agent prompts.
- `scripts/` for PowerShell-backed automation.
- `notes/registries/` for tracked, non-secret target metadata.
- `README.md` for the top-level operating model.

Relevant local assets include:
- `skills/tableau-cloud-auth-bootstrap.md`
- `skills/list-tableau-cloud-projects-and-content.md`
- `skills/publish-or-inspect-tableau-content.md`
- `scripts/tableau/auth-bootstrap.ps1`
- `scripts/tableau/auth-status.ps1`
- `scripts/tableau/list-projects.ps1`
- `scripts/tableau/list-content.ps1`
- `scripts/tableau/inspect-content.ps1`
- `scripts/tableau/publish-file.ps1`
- `notes/registries/tableau-targets.json`

## Gaps this upstream repo would fill for this workspace

No concrete gaps can be attributed to the upstream repository because its contents were not inspectable.

The only defensible conclusion is procedural: if the upstream repo contains reusable Tableau workflow knowledge, this workspace already has clear landing zones for selective recreation across `skills/`, `playbooks/`, `prompts/`, and `scripts/`.

## Conflicts or mismatches in auth model, platform assumptions, toolchain, naming, and workflow design

Confirmed mismatch risk from access model alone:
- The upstream repo requires enterprise authentication even for inspection.
- This workspace favors transparent, repeatable, local workflows documented in `README.md`.

Potential conflict areas to verify later if access is granted:
- Claude-specific or agent-specific assumptions.
- Mac or Bash-first execution patterns.
- Secret handling that conflicts with this repo's `.env.local` and registry model.
- Prompt-heavy workflows without concrete scripts.

## Recommended adoption plan

1. Do not adopt anything yet.
2. Obtain authenticated browser or Git read access.
3. Re-run the evaluation using the prompt in `prompts/evaluate-tableau-skills-repo.md`.
4. Prefer selective recreation over import.
5. Reject any asset that conflicts with this repo's secret-handling, Windows-first, or script-backed operating model.

## Reject or defer list

Reject now:
- Wholesale import.
- Submodule use.

Defer until access exists:
- Any asset-level adoption decision.
- Any prompt, skill, playbook, or script recreation plan.
- Any gap analysis that names specific upstream artifacts.

## Risks of wholesale import or submodule use

- Hidden auth assumptions.
- Platform mismatch.
- Secret handling drift.
- Maintenance coupling to a private upstream dependency.
- Blind adoption without code-level inspection.

## Inaccessible areas and follow-up access required

Inaccessible from this session:
- Repository tree
- README and docs
- File contents
- Folder structure
- Git refs beyond the auth boundary

Evidence gathered:
- Web fetch reached the repo host and redirected to identity-provider authentication.
- `git ls-remote` reported anonymous access denied.

Follow-up required:
1. Authenticated browser access to the repo UI, or
2. Authenticated Git read access sufficient to inspect the repository contents.

## Decision

Defer adoption analysis until authenticated inspection is possible. The correct next step is access, not implementation.
