# flowpilot-artifact-authority Specification

## ADDED Requirements

### Requirement: Formal work roles can read non-sealed project material

PM, Worker, Reviewer, and FlowGuard Operator SHALL be instructed that every non-sealed file under the current FlowPilot project root and current run root is ordinary readable work material when relevant to the current assignment.

#### Scenario: Relevant ordinary artifact is not named in authorized_result_reads
- **WHEN** a Worker, PM, Reviewer, or FlowGuard Operator needs a non-sealed evidence file, log, artifact, final output, acceptance contract, material understanding memo, or ledger under the current project/run roots
- **AND** that file is not a sealed body path
- **THEN** the role MAY read it directly without waiting for an `authorized_result_reads` grant
- **AND** the role MUST NOT skip the material solely because it is absent from `authorized_result_reads` or `material_artifact_map`.

### Requirement: Sealed bodies remain runtime-authorized only

Runtime SHALL keep startup/user-intake bodies, packet bodies, result bodies, PM decision bodies, Reviewer review bodies, and any `body_ref` marked sealed or `requires_runtime_open` unreadable by ordinary file access.

#### Scenario: Role sees a sealed body path
- **WHEN** a role sees a path/hash/envelope for a sealed body
- **THEN** the role MAY use the path/hash/envelope as navigation metadata
- **BUT** the role MUST NOT read the sealed body text unless runtime opens that body for the current role and current packet.

### Requirement: Controller remains body-redacted

Controller SHALL use only status, envelope, path, hash, lifecycle, and projection metadata for normal foreground work and MUST NOT read sealed role/user bodies.

#### Scenario: Controller patrol sees ordinary and sealed files
- **WHEN** Controller patrol renders current status
- **THEN** ordinary artifact metadata MAY be projected
- **AND** sealed body text MUST remain hidden.
