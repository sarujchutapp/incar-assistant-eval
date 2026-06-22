Status: ready-for-agent

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
