# Playbook: Python Source Change

Use this when changing `src/vali/` or Python-facing CLI behavior.

## Before editing

1. Read `AGENTS.md`.
2. Identify whether the change touches methodology-critical behavior:
   - `A`, `P`, `gA`, `gP`, `S_t`, `M_t`;
   - regime classification;
   - walk-forward validation;
   - label isolation;
   - liquidity/execution simulation;
   - KG manifest runtime constraints.
3. If methodology behavior changes, require explicit user approval and add or
   update tests first.

## Preferred workflow

1. Inspect current imports and compatibility facades.
2. Keep existing public imports working unless the task explicitly retires them.
3. Make a small, behavior-bounded edit.
4. Add narrow tests.
5. Run targeted tests.
6. Run the full suite when risk warrants it.

Workspace full-suite command:

```powershell
.\work\.venv\Scripts\python.exe -m pytest -q
```

## Do not

- Rewrite architecture opportunistically.
- Change formulas silently.
- Skip tests.
- Use live APIs unless explicitly scoped.
- Add credentials, live trading, order submission, or `P_flow`.
- Interpret performance as alpha without approved out-of-sample,
  execution-aware validation.

## Handoff checklist

Report:

- files changed;
- whether formulas/behavior changed;
- tests run and result;
- remaining risk;
- next recommended step.
