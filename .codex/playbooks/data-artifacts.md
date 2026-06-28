# Playbook: Data, Reports, and Artifacts

Use this when touching `data/`, `reports/`, `outputs/`, `artifacts/`, or
generated machine outputs.

## Data tiers

- `data/raw/`: immutable raw public source captures.
- `data/interim/`: normalized/transitional records.
- `data/processed/`: frozen analysis-ready inputs.
- `data/quarantine/`: provenance or reproducibility needs review.

## Report and artifact tiers

- `reports/runs/`: generated research runs.
- `reports/archive/`: retained reviewed reports.
- `reports/quarantine/`: reports requiring review.
- `artifacts/quarantine/`: stale builds or generated artifacts pending review.

## Rules

- Do not delete generated artifacts unless inventoried and approved.
- Do not rewrite raw data.
- Do not infer historical depth from volume, open interest, or trades.
- Do not promote fixture outputs into empirical evidence.
- Do not commit local absolute path artifacts into reviewer-facing docs.

## Preferred handling

1. Preserve raw generated outputs in quarantine if they contain local machine
   paths or require review.
2. Commit clean summaries or reproducing instructions instead of local-path
   raw artifacts.
3. Add tests for claim-boundary language when committing reports.

## Validation

Useful checks:

```powershell
.\work\.venv\Scripts\python.exe -m pytest tests\contract\test_artifact_layout_compatibility.py -q
.\work\.venv\Scripts\python.exe -m pytest tests\contract\test_submission_packaging.py -q
```
