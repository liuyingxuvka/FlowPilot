# FlowGuard Route Snapshot

## Route Decision

- Existing model preflight: reuse FlowPilot terminal/closure/resume,
  repair-transaction, and model-test-alignment boundaries.
- Model miss type: `boundary_missing` and `evidence_overclaimed`. The previous
  evidence proved terminal blocker recording and happy closure separately, but
  did not prove the composed repair-return loop.
- Downstream routes:
  - `model_miss_review` for root-cause backpropagation and same-class evidence.
  - `model_test_alignment` for obligation/code/test binding.
  - `development_process_flow` for evidence freshness, topology, and install
    sync ordering.

## Modeled Function Blocks

```mermaid
flowchart TD
  A["Terminal replay packet with segment_targets"] --> B["Reviewer result"]
  B --> C{"passed?"}
  C -->|false, valid blocker| D["Record semantic blocker"]
  D --> E["PM repair decision with opened blocker result"]
  E --> F["Terminal current-scope repair packet"]
  F --> G{"Packet has segment_targets?"}
  G -->|no| H["Mechanical reissue with terminal targets"]
  G -->|yes| I["Reviewer reruns terminal replay"]
  H --> I
  I --> J{"passed?"}
  J -->|false| D
  J -->|true| K["Clear blocker and record terminal replay"]
  K --> L["Final closure"]
```

## Evidence Freshness Rules

- Runtime/router edits stale focused runtime tests and core runtime checks.
- Fake E2E edits stale new entrypoint tests and fake project rehearsal
  evidence.
- Model-test alignment rows stale generated alignment results.
- Any source change under `skills/flowpilot` stales installed-skill sync and
  audit evidence.

## Minimum Revalidation

- Focused terminal repair-loop unit tests.
- Fake E2E terminal blocker repair-to-completion test.
- `python simulations/run_flowpilot_model_test_alignment_checks.py`.
- Field/contract checks.
- Core runtime and high-standard control-flow tests.
- Topology build/check.
- Install sync, install audit, install check, and `scripts/check_install.py`.
