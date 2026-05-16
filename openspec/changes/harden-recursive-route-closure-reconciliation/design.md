## Context

FlowPilot already has route-wide final ledgers, terminal backward replay, PM
closure approval, continuation quarantine, defect ledger templates, and
per-role memory templates. The remaining work is not a new subsystem; it is
making existing protocol promises executable in the router and model evidence.

## Decisions

### Parent/module traversal is explicit

`_next_effective_node_id` must treat an uncompleted non-root parent/module as
an executable scope. If a sibling parent has incomplete children, the next
frontier is the sibling parent itself, not the first leaf descendant. Existing
parent completion review remains unchanged: once all direct children are
completed, the parent/module is returned again for segment review and closure.

### Closure reconciliation is status-based and source-backed

Terminal closure collects three focused statuses:

- defect ledger: blocker-open and fixed-pending-recheck counts must be zero
  when a ledger is present; closed defects with required recheck evidence are
  counted separately;
- role memory: present role memory packets must belong to the current run and
  must not reuse historical agent ids as authority;
- imported artifacts/quarantine: continuation quarantine must keep prior control
  state, old agent ids, and old assets as audit/read-only evidence unless they
  are explicitly dispositioned for the current run.

Absent optional ledgers remain visible as `present=false` rather than being
treated as a pass claim. Dirty present ledgers block terminal closure.

### FlowGuard remains the architecture preflight

A focused FlowGuard model owns this pass instead of broadening the already
large parent models. It checks the unsafe cases directly: child-before-parent
entry, parent completion before child coverage, closure with unresolved
defects, closure with stale role memory, and closure with imported artifacts
still acting as current authority.

## Risks

- Over-strict closure checks could break older runs that do not have optional
  ledgers. Mitigation: absent optional ledgers are reported but do not block;
  dirty present ledgers block.
- Route traversal changes can affect sibling node order. Mitigation: keep the
  change local to non-root parent/module selection and update targeted runtime
  tests.
