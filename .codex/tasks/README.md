# VALI Codex Task Intake

Use this folder for future task briefs, migration slices, or mentor prompts that
should be preserved as reusable context.

Do not put secrets, credentials, private data, or live-trading instructions in
task files.

## Task brief template

```markdown
# Task: <short title>

## Goal

<What outcome should Codex produce?>

## Scope

- In scope:
- Out of scope:

## Constraints

- No formula changes unless explicitly approved.
- No `P_flow`.
- No private/proprietary inputs.
- No credentials, live trading, or order submission.
- Preserve public imports unless retirement is explicitly scoped.

## Files likely involved

- `src/vali/...`
- `tests/...`
- `docs/...`

## Required validation

```powershell
.\work\.venv\Scripts\python.exe -m pytest -q
```

## Stop condition

<When should Codex stop and report?>
```

## Suggested task categories

- `methodology-guardrail`
- `behavior-neutral-refactor`
- `provider-readonly`
- `kg-handoff`
- `docs-reviewer-surface`
- `operational-pilot`
- `data-remediation`
- `release-check`
