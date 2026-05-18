## Overview

The implementation uses a facade-first StructureMesh pattern. Each oversized public entrypoint keeps its original path and public behavior, while implementation details move into focused child modules. A split is only complete when the parent is below the diagnostic threshold, public behavior is still covered by tests, and the regenerated full diagnostic no longer reports an undeferred gap for that surface.

## Scope Boundaries

- In scope:
  - The 6 remaining `validation_gate` surfaces from `flowpilot_model_test_alignment_results.json`.
  - Clean `runtime_contract` surfaces whose files are not currently modified by peer agents.
  - External contract tests and diagnostic metadata required to prevent false coverage claims after child modules are introduced.
- Out of scope:
  - GitHub push, tag, release, or changelog publishing.
  - Peer-agent dirty files and unrelated complete OpenSpec changes.
  - Semantic rewrites of FlowPilot behavior beyond preserving split boundaries.

## Structure Strategy

Validation runners should become small wrappers that expose `main`, preserve the main guard, and import implementation from non-`run_*checks.py` child modules. This removes them from the validation-runner line threshold without changing command names.

Runtime modules should be split by owner responsibility:

- declarative tables into family shards;
- facade export tables into domain shards;
- route/frontier/artifact logic into policy, status, projection, and serialization shards;
- stateful runtime flows only when the child boundary has a stable external contract test.

Every parent facade should retain the old import path. Tests should assert either:

- child table union equals parent table;
- facade `__all__`/exported callable names still include expected public symbols;
- CLI parsing and JSON output options still work;
- model-code-test diagnostic reports no missing model/code/test and no internal-only test for newly introduced child surfaces.

## Validation Strategy

Minimum validation after code movement:

- `python -m py_compile` for every touched parent and child module.
- Focused contract tests for split runtime modules.
- `python -m unittest tests.test_flowpilot_model_check_runner_contracts`.
- `python -m unittest tests.test_flowpilot_model_test_alignment`.
- `python simulations\run_flowpilot_model_test_alignment_checks.py --json-out simulations\flowpilot_model_test_alignment_results.json`.
- StructureMesh and fast tier checks.
- Local install sync and audit after final source changes.

Long model checks may run in the background, but completion must be based on exit artifacts or foreground exit status, not progress logs.

## Peer Safety

Before staging or committing, compare `git status --short` to the intended file list. Stage only this OpenSpec change, its touched code/tests/docs/results, and the local adoption note section for this change. Do not stage peer dirty files even if validation commands update their generated results.
