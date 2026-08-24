# Releasing `aiosolaredge-one`

This package is published to PyPI with **Trusted Publishing** (OIDC) — GitHub
Actions authenticates to PyPI directly, so there are **no API tokens** stored in
the repo or in GitHub secrets.

Workflow: [`.github/workflows/publish.yml`](.github/workflows/publish.yml)
- **Manual run** (`workflow_dispatch`) → **TestPyPI** (`testpypi` environment)
- **GitHub Release published** → **PyPI** (`pypi` environment)

## 0. Prerequisites (once)

The repo is at **`CathalOConnorRH/solaredge-v2`** and `[project.urls]` in
[`pyproject.toml`](pyproject.toml) already point there. If you fork or rename,
update those URLs and the trusted-publisher config below to match.

## 1. One-time Trusted Publisher config

Do this on **both** TestPyPI and PyPI. You do **not** need to create the project
first — use a "pending" publisher and it's created on first upload.

### TestPyPI
1. Sign in at <https://test.pypi.org> → *Your account* → *Publishing*.
2. Under **Add a new pending publisher**, enter:
   - **PyPI Project Name:** `aiosolaredge-one`
   - **Owner:** `CathalOConnorRH`
   - **Repository name:** `solaredge-v2`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `testpypi`

### PyPI
Repeat at <https://pypi.org> with the **same** values except:
   - **Environment name:** `pypi`

### GitHub environments (optional but recommended)
In the GitHub repo → *Settings* → *Environments*, create `testpypi` and `pypi`.
Add required reviewers on `pypi` if you want a manual approval gate before a real
release upload.

## 2. Dry run to TestPyPI

GitHub → *Actions* → **Publish aiosolaredge-one** → **Run workflow** (on `main`).
This builds, `twine check`s, and uploads to TestPyPI. Verify the install:

```bash
python -m venv /tmp/veitest && /tmp/veitest/bin/pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  aiosolaredge-one==0.2.0
/tmp/veitest/bin/python -c "import aiosolaredge_one, sys; print(aiosolaredge_one.__version__)"
```

(The `--extra-index-url` lets TestPyPI resolve real deps like `aiohttp`.)

## 3. Release to PyPI

1. Bump `version` in `pyproject.toml` **and** `src/aiosolaredge_one/__init__.py`
   (`__version__`), add a `CHANGELOG.md` entry, commit.
2. Tag and create a GitHub Release:
   ```bash
   git tag v0.2.0 && git push origin v0.2.0
   gh release create v0.2.0 --title v0.2.0 --notes-from-tag
   ```
3. Publishing the release triggers the `pypi` job automatically.

Keep the release tag (`vX.Y.Z`) in sync with the package version. The HA
integration lives in its own repo
([`ha-solaredge-one`](https://github.com/CathalOConnorRH/ha-solaredge-one)) and
pins `aiosolaredge-one==<version>` in its `manifest.json`; after publishing a new
library version, bump that pin (and the integration `version`) there so a
released integration always installs a published library.

## Manual fallback (if not using CI)

Trusted Publishing is preferred, but you can upload from a laptop with an API
token:

```bash
python -m pip install ".[publish]"
rm -rf dist && python -m build && python -m twine check dist/*
python -m twine upload --repository testpypi dist/*   # dry run
python -m twine upload dist/*                          # real PyPI
```
