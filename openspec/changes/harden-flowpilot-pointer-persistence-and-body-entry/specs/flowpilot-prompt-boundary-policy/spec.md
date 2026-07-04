## ADDED Requirements

### Requirement: Formal output prompts prefer body-file submission
FlowPilot prompt and card policy SHALL direct formal packet results, reports,
decisions, and blockers to be written as run-scoped JSON object files and
submitted with `flowpilot_new.py submit-result --body-file` by default.

#### Scenario: Shared return policy names body-file
- **WHEN** a runtime-kit card or packet prompt includes the common formal
  output return path
- **THEN** it MUST prefer `submit-result --body-file <path>` for sealed result
  submission
- **AND** it MUST still preserve the rule that result body content stays out of
  chat.

#### Scenario: Inline body is not the default
- **WHEN** generated role, phase, event, or system cards are checked for the
  common return policy
- **THEN** they MUST NOT advertise raw `--body <sealed_result_summary>` paste as
  the default formal return path.

#### Scenario: Prompt policy remains current-contract only
- **WHEN** prompt/card text describes body submission failures
- **THEN** it MUST require a top-level JSON object and MUST NOT suggest
  compatibility conversion from quoted JSON strings.
