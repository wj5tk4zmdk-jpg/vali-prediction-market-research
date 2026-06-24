# VALI Environment

VALI requires Python 3.12 or newer. Runtime and optional development
dependencies are declared in `pyproject.toml`; the supported local installation
form evident from the project metadata is:

```powershell
python -m pip install -e ".[dev]"
```

Notebook work additionally uses the `notebook` optional dependency group. No
lock file is currently committed, so exact transitive dependency resolution is
not yet guaranteed across machines.

The current repository test command is:

```powershell
& '.\work\.venv\Scripts\python.exe' -m pytest -q
```

`work/.venv` is local environment state. It is not research data, a frozen
analysis input, or a distributable artifact. Imports must resolve from
`src/vali`; quarantined build artifacts must never be added to `PYTHONPATH` or
used as an installation source.

The Google Trends integration is an offline-ready interface and fixture
gateway. No live official Google Trends API client is implemented. The Kalshi
integration is public and read-only; credentialed trading and order submission
do not exist in this repository.
