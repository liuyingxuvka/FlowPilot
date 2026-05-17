## ADDED Requirements

### Requirement: Router facade remains the public entrypoint

`flowpilot_router.py` SHALL remain the public Python import and CLI entrypoint
while behavior families are moved into cohesive internal modules.

#### Scenario: CLI entrypoint remains compatible

- **GIVEN** a maintainer runs the existing router CLI command
- **WHEN** router behavior has been moved into child modules
- **THEN** `flowpilot_router.py` SHALL continue to parse and dispatch the
  command through the same public entrypoint.

### Requirement: Router behavior is split by cohesive state ownership

Router child modules SHALL own cohesive behavior families and SHALL NOT be
generated as one top-level function per file.

#### Scenario: Split plan is reviewed

- **GIVEN** a router split plan
- **WHEN** FlowGuard reviews module ownership
- **THEN** every behavior partition SHALL have exactly one owner module
- **AND** the plan SHALL reject micro-module explosion as a maintainability
  hazard.

### Requirement: Prompt content is externalized through PromptStore

Prompt-like control text moved out of Python SHALL live in
`runtime_kit/prompts/` and be loaded through PromptStore with manifest and hash
validation.

#### Scenario: Router builds a prompt delivery action

- **GIVEN** a router action references a prompt id
- **WHEN** PromptStore renders the prompt
- **THEN** the prompt asset SHALL exist
- **AND** the content hash SHALL match the prompt manifest
- **AND** the router SHALL NOT silently fall back to stale inline text.

### Requirement: Background validation needs final artifacts

Long-running router checks SHALL only be reported complete after final
background artifacts have been inspected.

#### Scenario: Background run only has progress output

- **GIVEN** a long router check wrote progress lines
- **AND** no final exit artifact or completed metadata exists
- **WHEN** the validation result is summarized
- **THEN** the result SHALL be treated as incomplete, not passed.
