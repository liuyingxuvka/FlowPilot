## ADDED Requirements

### Requirement: ACK Clearance Uses Closure Kernel Without Completing Work
System-card ACK clearance SHALL use the shared closure kernel to decide whether
the ACK/read obligation is mechanically settled, while preserving the existing
separation between ACK settlement and semantic output-work completion.

#### Scenario: ACK row closes read obligation only
- **WHEN** a system-card ACK return is classified as `closed_success`
- **THEN** Router clears the scoped read obligation and MUST keep any associated
  worker, PM, reviewer, or officer output obligation open until its own evidence
  closes

#### Scenario: Missing ACK evidence remains blocking
- **WHEN** a system-card ACK row has a closed-looking status but lacks the
  required ACK envelope, receipt, or original-card identity
- **THEN** the closure kernel classifies the ACK obligation as repair-required
  or incomplete, and Router MUST NOT cross the protected boundary
