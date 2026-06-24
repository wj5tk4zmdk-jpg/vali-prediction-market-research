# VALI Clean-Clone Installation Test

## Summary

The repository passed a clean-clone installation and validation test using
committed files and documented `.venv` setup instructions.

## Repository identity

- Repository: `wj5tk4zmdk-jpg/vali-prediction-market-research`
- Clone URL:
  `https://github.com/wj5tk4zmdk-jpg/vali-prediction-market-research.git`
- Commit tested: `3f1329e2708d6e8ab24eecfeefb5c8f5ccaa9e70`
- Branch: `main`

## Environment

- Python: `3.12.13`
- Fresh virtual environment: `.venv`
- Initial `.venv`: absent
- Initial `work/.venv`: absent

## Commands

```powershell
git clone https://github.com/wj5tk4zmdk-jpg/vali-prediction-market-research.git
cd vali-prediction-market-research
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m vali --help
```

On the test machine, an available Python 3.12.13 interpreter bootstrapped the
fresh `.venv`; the documented `py -3.12` command is the standard Windows
equivalent. Installation, validation, and CLI checks then ran exclusively
through that fresh environment.

## Results

- Installation: **passed**
- Full test suite: **186 passed, 0 failed**
- CLI smoke checks: **15 passed**
- Reviewer artifacts: **9/9 present**
- Leaked local environment: **none**; no leaked `work/.venv` was present

## Claim boundaries

- This result proves clean installation and test reproducibility at the tested
  commit.
- It does not prove empirical alpha.
- It does not prove trading readiness.
- No live API was used.
- No credentials were used for tests.
- No private data was used.
- No proprietary order flow was used.
- No order submission exists.
- No `P_flow` exists.

## Conclusion

The repository is ready for reviewer access subject to remaining human
submission decisions: license, visibility, optional GitHub Pages, and
application submission.
