# Task handoff

- **Updated**: 2026-11-01
- **Agent**: Antigravity / Gemini 3.8 Flash
- **Status**: done
- **Goal**: Configure GitHub Actions workflow for PyPI Trusted Publishing via OIDC.

## Done

- **GitHub Actions Workflow**:
  - Created `.github/workflows/publish.yml` with `release: published` trigger and manual `workflow_dispatch`.
  - Configured `pypa/gh-action-pypi-publish@release/v1` with `id-token: write` permission and `environment: pypi` for PyPI Trusted Publishing (OIDC), without API tokens or passwords.
  - Implemented dual-job architecture:
    - `build`: Isolated sdist & wheel build, `twine check --strict`, `check-wheel-contents`, and venv smoke testing (verifying `mlog`, `mlog-py`, and 0 `src` leaks).
    - `publish-to-pypi`: Dedicated publish job scoped to environment `pypi` and OIDC token generation.
- **Documentation**:
  - Updated `README.md` to document `pip install mlog-py` under Installation.
  - Added "Release & Publishing" section explaining PyPI Trusted Publisher configuration steps (Owner: `annguyen2k8`, Repo: `mlog-py`, Workflow: `publish.yml`, Environment: `pypi`).
- **Verification**:
  - Validated YAML syntax with `pyyaml`.
  - Verified clean sdist and wheel build: `twine check --strict` passed, `check-wheel-contents` passed, 0 `src` leaks in wheel.
  - Verified `git diff --check`: 0 issues.
  - Created clean local commit. Did not push to remote.

## Next

- User configures Trusted Publisher on PyPI (`mlog-py` -> GitHub -> `annguyen2k8/mlog-py`, `publish.yml`, environment `pypi`).
- User creates GitHub environment `pypi` in repository settings.

## Blocked

- none

## Verification

- `python -c "import yaml; yaml.safe_load(open('.github/workflows/publish.yml'))"`: valid YAML.
- `twine check --strict` on clean build: PASSED.
- `check-wheel-contents` on clean wheel: PASSED.
- `python -m unittest tests.test_agent_memory -v`: 6/6 passed.
- `python -m unittest tests.test_compiler_examples -v`: 4/4 passed.
- `git diff --check`: 0 issues.
