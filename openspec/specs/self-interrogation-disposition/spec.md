# self-interrogation-disposition Specification

## Purpose
TBD - created by archiving change persist-self-interrogation-findings. Update Purpose after archive.
## Requirements
### Requirement: Self-interrogation findings are durable evidence

FlowPilot SHALL represent meaningful grill-me/self-interrogation findings in a
durable `flowpilot.self_interrogation_record.v1` artifact or in a PM suggestion
ledger entry that cites such a source.

#### Scenario: PM finishes startup self-interrogation

Given a formal route is before product architecture or root contract freeze
When PM completes startup self-interrogation
Then PM records the scope, source, findings, and PM disposition state in a
self-interrogation record
And Router can find the record through the route self-interrogation index.

#### Scenario: Reviewer surfaces a hard challenge

Given a reviewer performs self-interrogation while reviewing an artifact
When the reviewer finds a hard blocker or useful nonblocking route concern
Then the reviewer emits a structured PM suggestion candidate or cites an
existing PM suggestion ledger entry
And the reviewer output cites the self-interrogation source.

### Requirement: PM dispositions meaningful findings before protected gates

FlowPilot SHALL require PM to disposition every hard/current
self-interrogation finding before protected gates advance.

#### Scenario: Root contract freeze has unresolved startup finding

Given the self-interrogation index contains a startup or product architecture
record with unresolved hard findings
When PM attempts to freeze the root acceptance contract
Then Router rejects the freeze
And the rejection names the unresolved self-interrogation finding source.

#### Scenario: Node packet dispatch has unresolved node-entry finding

Given a current node has a node-entry self-interrogation record
And that record contains unresolved hard findings
When PM attempts to register or dispatch the current-node packet
Then Router rejects packet progress
And PM must incorporate, defer, ledger, reject, or waive the finding first.

### Requirement: Final closure cites self-interrogation disposition

FlowPilot SHALL include self-interrogation record coverage in the final
route-wide ledger and terminal closure checks.

#### Scenario: Final ledger omits the self-interrogation index

Given the route has self-interrogation records
When PM writes the final route-wide ledger without citing the index and clean
self-interrogation disposition state
Then Router rejects the final ledger.

#### Scenario: Terminal closure sees unresolved self-interrogation findings

Given the final ledger or self-interrogation index reports unresolved hard or
current findings
When PM attempts terminal closure
Then Router rejects closure.

### Requirement: Router checks mechanics, not semantic quality

FlowPilot SHALL keep Router validation mechanical for self-interrogation
records.

#### Scenario: Record has a PM rejection reason

Given a finding is rejected with PM owner, reason, and residual-risk statement
When Router validates a protected gate
Then Router treats the finding as dispositioned
And Router does not judge whether the PM reasoning is persuasive.

#### Scenario: Record is malformed

Given a self-interrogation record is missing stable ids, scope, owner role,
severity, disposition, or source path for a finding
When Router validates a protected gate
Then Router rejects the gate with a schema/shape error.
