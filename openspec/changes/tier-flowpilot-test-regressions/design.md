## Overview

This is a validation-structure change. It does not weaken any existing
release gate; it moves those gates into explicit tiers so local routine work
can use the smallest trustworthy boundary and long regressions can run in the
background with completion evidence.

## Risk Intent

- Prevent root pytest collection from scanning backup or temporary tests.
- Prevent long model/release regressions from entering the foreground fast
  loop.
- Prevent background progress lines from being reported as pass/fail evidence.
- Prevent hidden skips, stale child-suite evidence, or duplicate partition
  ownership from creating false parent confidence.
- Keep release-required suites visible even when routine tiers defer them.
- Preserve install/local-sync visibility for any new validation surface.

## Test Tier Structure

- `collect`: verifies pytest discovery is scoped to `tests/`.
- `fast`: runs the focused TestMesh model and small maintenance/proof tests.
- `router-*`: runs child slices for router startup, foreground/controller,
  packet/card/ACK, route mutation, and terminal/closure behavior.
- `router`: parent tier that runs the router child slices without requiring the
  legacy aggregate runtime file.
- `integration`: runs install, local sync audit, smoke fast, and read-only
  FlowGuard coverage sweep.
- `release`: runs release/public-boundary validation and makes full-regression
  obligations explicit.
- `legacy-full`: runs heavyweight Meta and Capability full regressions only
  when explicitly selected, normally in the background.

## Background Contract

Background tiers write one artifact set per command under the selected log
root:

- `<name>.out.txt`
- `<name>.err.txt`
- `<name>.combined.txt`
- `<name>.exit.txt`
- `<name>.meta.json`

The runner may report that a job was launched after creating metadata, but it
must not report a background command as passed until the exit artifact exists
and the exit code is inspected.

## Validation Strategy

- `python simulations/run_flowpilot_test_tiering_checks.py --json-out simulations/flowpilot_test_tiering_results.json`
- `python -m pytest tests/test_flowpilot_test_tiers.py -q`
- `python scripts/run_test_tier.py --tier fast --dry-run --json`
- `python scripts/run_test_tier.py --tier integration --dry-run --json`
- `python scripts/check_install.py --json`

Long release and legacy full tiers can be launched with `--background` and
then inspected from their artifact metadata.
