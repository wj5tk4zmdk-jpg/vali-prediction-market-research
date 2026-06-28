# Playbook: Documentation or Reviewer Artifact Change

Use this for `README.md`, `docs/`, `reports/`, submission HTML/Markdown, and
researcher-facing guides.

## Source-of-truth rule

If an HTML page is generated from Markdown, edit the Markdown source and
regenerate the HTML using the existing script. Do not hand-edit generated HTML
unless the page is intentionally standalone.

Known standalone HTML:

- `docs/submission/VALI_EXPLORER.html`
- `docs/knowledge_graph/VALI_KNOWLEDGE_GRAPH_EXPLAINER.html`

## Claim boundaries

Every reviewer-facing or research-facing document must preserve:

- no empirical alpha claim;
- no trading-readiness claim;
- no private data;
- no proprietary order flow;
- no credentials;
- no live trading;
- no order submission;
- no `P_flow`;
- honest blocker language when data is insufficient.

## Local paths

Submission-facing docs must not contain local absolute paths such as
`C:\Users\...` or `C:/Users/...`.

Historical logs may retain local paths when they document actual prior runs.
Do not rewrite historical provenance casually.

## Validation

Run relevant contract tests after doc changes. Common starting points:

```powershell
.\work\.venv\Scripts\python.exe -m pytest tests\contract\test_submission_packaging.py -q
.\work\.venv\Scripts\python.exe -m pytest tests\contract -k knowledge_graph -q
```

Run the full suite before committing broad reviewer-surface changes.
