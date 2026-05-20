## Overview

The upgrade folds several scattered control-plane tables into a small contract kernel without removing FlowPilot's hard boundaries. Controller still watches the foreground, workers still cannot read each other's private bodies, and signed packet/result envelopes still protect the relay boundary.

The change is not "compressing the workflow" from the user's point of view. It removes duplicate code paths that currently describe the same obligation in different ways.

## Contract Kernel

The kernel has four practical rules:

1. **Artifact authority**: signed envelopes are original records; indexes, scheduler rows, ledgers, and migration sidecars are mutable projections.
2. **Action identity**: one Controller table row represents one Router obligation. A control blocker is not identified only by label and target role; its `blocker_id` and artifact path are part of identity.
3. **Receipt effect**: a `done` receipt for stateful Controller work must either apply or reclaim a Router-visible postcondition. Otherwise it remains incomplete and repairable.
4. **Reviewer package release**: PM may hide raw worker result bodies from Reviewer only if PM writes an equivalent formal gate package with path, hash, scope, and content boundary.

## Implementation Shape

- Add a narrow Python registry module under `skills/flowpilot/assets/` for shared control-plane contract helpers.
- Use that registry from existing owner modules instead of adding another parallel ledger.
- Keep compatibility facades intact; the registry is an internal helper, not a new public command surface.
- Extend the existing `flowpilot_control_plane_friction` FlowGuard model instead of creating an unrelated model island.

## Migration Behavior

Legacy material packet repair keeps its current purpose, but changes where it writes:

- If an envelope has not been Controller-relayed, the legacy backfill may update the envelope as before.
- If an envelope has a Controller relay signature, repair must not rewrite the envelope file or signed embedded envelope copies.
- For signed envelopes, repair writes index/ledger projection fields plus `material/legacy_material_packet_migration.json` sidecar records.

## Safety Boundaries

- Controller remains envelope-only and never gains sealed body reads.
- Worker results still relay to PM first where PM owns absorption.
- Reviewer receives PM formal package artifacts, not raw worker body files.
- Existing pending action compatibility remains, but Controller scheduler rows now carry stronger identity and replayable postcondition metadata.

## Risks

- Some legacy fixtures may assert exact old row IDs; focused tests should assert identity separation instead of hardcoded hashes.
- The receipt path touches active peer work in the same area. The implementation should avoid unrelated wait-reminder replay changes and stage only intentional hunks.
- Formal package artifacts add files to run directories, so tests must verify hashes rather than rely on directory file counts.
