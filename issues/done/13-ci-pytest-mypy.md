Status: done

# CI: run pytest + mypy on merge requests

## Parent

PRD #1 · roadmap item #7 (`reserch/roadmap.md`)

**GitLab:** #14

## What to build

A `.gitlab-ci.yml` that installs the package and runs the feedback loops (`python -m pytest`, `python -m mypy`) on merge requests, so the deterministic suite gates changes.

## Acceptance criteria

- [ ] Pipeline installs `.[dev]` and runs pytest + mypy
- [ ] Green on the current main; fails on a deliberately broken test
- [ ] Runs without network (fixtures only)

## Blocked by

None — can start immediately.

## Comments

### Done — 2026-06-22

`.gitlab-ci.yml` added: `python:3.12-slim` image, single `test` stage with two
jobs (`pytest`, `mypy`), gated to `merge_request_event`. `before_script` does
`pip install -e ".[dev]"`. Verified:

- [x] Installs `.[dev]`, runs `python -m pytest` + `python -m mypy`
- [x] Green on current main (both exit 0; 111 passed, mypy clean over 30 files)
- [x] Fails on a deliberately broken test / type error (both exit 1, canary
      files added then removed — no residue)
- [x] Test suite itself touches fixtures only (FakeModelClient; no live client
      wired — that's #12, blocked on creds)

Note: the runner's `pip install` step does reach PyPI to provision deps — that's
runner setup, not the evaluation. The "no network (fixtures only)" criterion is
about the suite not making live model/API calls, which holds.
