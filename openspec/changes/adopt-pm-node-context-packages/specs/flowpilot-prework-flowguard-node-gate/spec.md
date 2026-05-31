## MODIFIED Requirements

### Requirement: Route nodes require pre-work FlowGuard before worker execution

FlowPilot SHALL require each current executable route node to have a current
accepted PM node context package and a current accepted pre-work FlowGuard gate
before issuing the node's worker task packet.

#### Scenario: PM node plan is accepted before FlowGuard pre-work gate

- **WHEN** a route node has a PM node design or node acceptance plan accepted
- **AND** the accepted plan contains a current node context package
- **THEN** runtime MUST issue a FlowGuard pre-work packet for that node
- **AND** runtime MUST NOT issue the worker node task packet until that
  FlowGuard packet passes for the node's current repair generation.

#### Scenario: Direct worker task issuance is blocked before pre-work pass

- **WHEN** a caller asks runtime to issue a node worker packet
- **AND** the current node lacks an accepted current-generation node context
  package or pre-work FlowGuard report
- **THEN** runtime MUST reject worker packet issuance and expose the missing
  gate as the next required route action.
