# VALI Environment

VALI requires Python 3.12 or newer. Runtime and optional development
dependencies are declared in `pyproject.toml`.

From a fresh clone, use an isolated environment. PowerShell:

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -e ".[dev]"
& '.\.venv\Scripts\python.exe' -m pytest -q
& '.\.venv\Scripts\python.exe' -m vali --help
```

POSIX shells:

```sh
python3.12 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
./.venv/bin/python -m pytest -q
./.venv/bin/python -m vali --help
```

Notebook work additionally uses the `notebook` optional dependency group. No
lock file is currently committed, so exact transitive dependency resolution is
not yet guaranteed across machines.

`.venv` is local environment state and is excluded from version control. It is
not research data, a frozen analysis input, or a distributable artifact.
Imports must resolve from `src/vali`; quarantined build artifacts must never be
added to `PYTHONPATH` or used as an installation source.

The Google Trends integration is an offline-ready interface and fixture
gateway. No live official Google Trends API client is implemented. The Kalshi
integration is public and read-only; credentialed trading and order submission
do not exist in this repository.
