# Harden FlowPilot Stage Evidence Matrix

## Why

FlowPilot's current contract path correctly requires a high-standard
acceptance registry, current packet result shapes, FlowGuard checks, Reviewer
checks, and final backward replay. The missing piece is a single machine-owned
stage/evidence matrix that tells every gate what the current packet is proving
now and what must be proved later.

Without that matrix, the first PM high-standard contract can list future
closure evidence for every acceptance item, and a FlowGuard operator can
mistake those future evidence rows for evidence that must already exist in the
preplanning packet. That blocks a valid first package before route work starts.

## What Changes

- Add a current-contract stage/evidence matrix shared by runtime, prompt cards,
  FlowGuard models, fake-AI parity checks, install checks, and tests.
- Mark the PM high-standard contract packet as a preplanning contract-definition
  package: it must define requirements and the acceptance registry, but it must
  not be blocked for missing Worker output, route-node evidence, target-product
  proof, or final backward replay evidence unless the PM claims that evidence
  already exists.
- Mark node acceptance plans as plan-stage packages with the same rule: they
  must project expected evidence and owner nodes, but must not be blocked for
  missing Worker result evidence before Worker dispatch.
- Preserve strict result-stage and terminal-stage evidence gates for Worker
  results, PM dispositions, FlowGuard reports, Reviewer reports, and final
  backward replay.
- Add a portable installed FlowPilot runtime self-check receipt so target
  projects do not need the development repository's `simulations/` scripts for
  first-run FlowGuard package evidence.
- Bind the matrix to FieldLifecycleMesh, information-flow alignment,
  model-test alignment, contract exhaustion, Cartesian coverage, unit tests,
  install checks, and local install sync.

## Non-Goals

- Do not remove or weaken final direct-evidence closure standards.
- Do not add fallback parsing, legacy aliases, shape guessing, or old-field
  compatibility.
- Do not add a second packet protocol, second reviewer lane, or route-candidate
  ledger.
- Do not require target projects to contain FlowPilot development regression
  scripts.
- Do not overwrite unrelated peer-agent edits.

