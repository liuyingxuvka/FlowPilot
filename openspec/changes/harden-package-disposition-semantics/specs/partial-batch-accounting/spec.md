## ADDED Requirements

### Requirement: Batch member summaries expose PM outcomes
Each Router-owned packet batch SHALL record the PM package disposition outcome for each member packet when a PM package-result disposition is recorded.

#### Scenario: Mixed PM packet outcomes
- **WHEN** a PM disposition records accepted outcome for one packet and rework outcome for another packet in the same batch
- **THEN** the batch summary records each packet's PM outcome next to its packet id and target role
- **AND** aggregate advancement remains blocked until the rework outcome is resolved through an authorized path

### Requirement: Absorption requires all blocking members accepted
The Router SHALL NOT mark a package batch as PM-absorbed when any blocking member packet has a PM outcome other than accepted.

#### Scenario: Aggregate absorbed contradicts packet rework
- **WHEN** a PM package-result disposition has aggregate decision `absorbed`
- **AND** any member packet outcome is `rework_requested`, `blocked`, `canceled`, or `route_or_node_mutation_required`
- **THEN** the Router rejects the disposition instead of writing a contradictory absorbed batch state
