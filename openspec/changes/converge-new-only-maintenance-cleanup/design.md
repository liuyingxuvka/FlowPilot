## Context

The previous compatibility-removal change made the active runtime reject old command,
event, transaction, and prompt paths. A follow-up read-only FlowGuard audit found that
the runtime is mostly clean, but maintenance surfaces still create confusion:

- active OpenSpec specs still describe retired paths as accepted aliases;
- current model evidence sometimes exists twice as `*_checks_results.json` and
  `*_results.json`;
- one stale dynamic-return result artifact still teaches retired aliases;
- packet and gate helper modules retain empty/no-op alias functions;
- the largest runtime cards and router test helpers remain harder to maintain than
  their current obligations require.

## Goals / Non-Goals

**Goals:**

- Make the active specifications match the new-only runtime contract.
- Canonicalize result evidence without weakening parent/child model proof.
- Remove alias hooks only when real code and tests already prove current rejection or
  canonical behavior.
- Reduce prompt/test maintenance load while preserving required card terms, role
  boundaries, current fallbacks, and rejection tests.
- Sync the installed local FlowPilot skill and commit the final local repository state.

**Non-Goals:**

- No release, push, tag, deploy, binary packaging, or default-branch publication.
- No deletion of `.flowpilot/runs`, backups, or archived OpenSpec history.
- No removal of current fallback safety paths: manual resume, Cockpit display fallback,
  authorized single-agent fallback, or controller break-glass repair.
- No broad router rewrite or public API contraction without parity evidence.

## Decisions

### Decision: classify old words before deleting them

Retired terms can mean different things. Rejection tests and known-bad model
cases remain valid when they prove old inputs fail. Active specs, prompts, code hooks,
or result artifacts that present those inputs as accepted old paths must be
updated or removed.

### Decision: canonical result files are `*_results.json`

When a model/check family has both a shadow `*_checks_results.json` and a current
`*_results.json`, the current result file is the canonical proof artifact. Parent
evidence selectors must prefer that canonical artifact before deleting shadow files.

### Decision: no-op alias hooks are removable only with conformance coverage

`GATE_CONTRACT_ALIASES` and `normalize_envelope_aliases()` no longer translate any
current input. Remove them only after import sites are updated and packet alias
rejection tests still pass.

### Decision: prompt compression is obligation-preserving

Runtime cards may be shortened by removing duplication, but required identity,
runtime return, FlowGuard work-order, sealed-body, fallback, and authority language
must remain checkable by existing prompt/card validators.

### Decision: validation order matters

Run focused checks after each behavior-bearing cleanup, then run install sync/audit,
OpenSpec validation, and background heavyweight FlowGuard regressions. Do not report
background logs as pass evidence until exit artifacts and metadata are inspected.

## Risks / Trade-offs

- Deleting shadow result artifacts can stale parent evidence. Mitigation: update
  selection logic first, regenerate parent evidence, then delete only files with
  canonical current replacements.
- Prompt compression can remove terms required by install/card checks. Mitigation:
  run card coverage and install checks immediately after prompt edits.
- Removing no-op helper functions can break imports even if behavior is unchanged.
  Mitigation: update facades/imports and run packet/runtime tests.
- Parallel AI work may arrive during implementation. Mitigation: recheck git status
  before edits and avoid reverting unrelated paths.

## Validation Plan

1. FlowGuard import/version check.
2. OpenSpec change/spec validation.
3. Focused unit tests for repair transaction rejection, packet alias rejection,
   card/prompt coverage, artifact audit, and install checks.
4. Regenerate affected model result artifacts where canonical evidence changes.
5. Run background meta and capability regressions under `tmp/flowguard_background/`
   and inspect `.exit.txt`/`.meta.json`/combined logs.
6. Sync local installed FlowPilot skill and run install freshness audit.
7. Final git diff/status audit and local commit.
