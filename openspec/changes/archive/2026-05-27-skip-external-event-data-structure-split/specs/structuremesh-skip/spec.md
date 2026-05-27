## ADDED Requirements

### Requirement: Table-Only StructureMesh Skip

The full model-test-code diagnostic SHALL allow a StructureMesh candidate to be
explicitly skipped only when the surface is table-only and the skip evidence is
visible in the diagnostic payload.

#### Scenario: External-event data table is skipped instead of split

- **WHEN** `flowpilot_router_protocol_external_event_data.py` remains above the
  generic StructureMesh line threshold
- **AND** the surface has no top-level functions or classes
- **AND** external contract tests still prove phase-table parity with the
  public external-event registry and child shards
- **THEN** the diagnostic SHALL set `split_status` to `skipped_split`
- **AND** it SHALL set `structure_split_status` to `explicitly_skipped`
- **AND** it SHALL not emit a `needs_structure_split` finding for that surface
- **AND** it SHALL expose the skipped surface in
  `explicitly_skipped_structure_split_surfaces`
