# Playbook: Commit, Push, or Release Check

Use this before committing, pushing, or preparing a handoff.

## Pre-commit checks

1. Inspect scope:

```powershell
git status --short
git diff --stat
```

2. Run targeted tests for changed areas.
3. Run the full suite for methodology, CLI, docs, KG, or submission-surface
   changes:

```powershell
.\work\.venv\Scripts\python.exe -m pytest -q
```

4. Collect the test count when reporting:

```powershell
.\work\.venv\Scripts\python.exe -m pytest --collect-only -q
```

## Commit rules

- Commit only the scoped files.
- Do not push unless the user or mentor explicitly asks.
- Never use destructive Git commands unless explicitly requested.
- Confirm whether generated or quarantined artifacts are intentionally ignored
  or intentionally committed.

## Handoff report

Include:

- commit hash if committed;
- push status if pushed;
- working-tree status;
- test command and result;
- collected test count;
- boundary confirmation.
