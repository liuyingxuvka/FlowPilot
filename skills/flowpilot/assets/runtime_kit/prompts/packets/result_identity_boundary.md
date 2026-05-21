---
$result_identity_marker: true
completed_by_role: $role
completed_identity: I completed this as `$role` for the source packet only.
allowed_scope: Report only work performed under the source packet and allowed evidence.
forbidden_scope: I did not approve gates unless my role is the approver; do not claim another role's authority, bypass Router, communicate outside the mail system, or hide unresolved issues.
required_return: Submit current active-holder packet completion directly to Router when a lease is present; otherwise send this result body only through the Router-directed runtime path. The chat response must contain envelope metadata only.
controller_aside: The result envelope may include an optional `controller_aside` for a short Controller-only process/status note. It is not evidence, not a finding, not a recommendation, not an approval, and not a Router event source.
mail_only_reminder: Active-holder completion goes to Router first; later role-to-role communication for this result is relayed by Controller only when Router instructs it.
---
