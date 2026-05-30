# FlowPilot Similarity Convergence

FlowPilot now has a FlowGuard similarity-convergence gate:

```powershell
python simulations/run_flowpilot_similarity_convergence_checks.py --json-out simulations/flowpilot_similarity_convergence_results.json
```

This gate answers four maintenance questions before a broad cleanup or branch
fold is trusted:

- Which model branches are the same maintenance family?
- If a bug was fixed in one branch, which siblings must be checked?
- Which branches look similar but are false friends and must stay separate?
- Which fold candidates are only future architecture-reduction work because
  runtime replay or StructureMesh evidence is still required?

The gate is intentionally non-runtime. It does not change protocol behavior.
It produces a model report that is consumed by documentation, install checks,
and model-test alignment.

## Current Maintenance Groups

| Group | Shared concern | Variant boundaries |
| --- | --- | --- |
| Packet result return reconciliation | Durable result envelopes must fold into Router result-return events before stale waits. | Material scan, research, current node, and PM role-work keep separate event names and sealed-body boundaries. |
| ACK return reconciliation | Duplicate or late ACKs must not reopen resolved return waits. | Single card, bundle card, and system-card returns keep their own payload and completion rules. |
| Route mutation replacement | Route repair must invalidate stale evidence, supersede old current-node packets, and declare replay scope. | Ordinary supersede and sibling branch replacement keep topology-specific requirements. |
| Router reconciliation result cases | Reconciliation branches map to a small result-case vocabulary. | Scheduled receipts, direct role-output events, and runtime resume projections keep separate authority and state-write rules. |

## False-Friend Boundary

Route display refresh and route mutation can both mention sibling replacement.
They are not the same owner:

- route mutation owns route draft, frontier, stale evidence, packet supersession,
  and replay scope;
- route display is derived evidence for user-visible route signs and diagrams;
- a display helper must not gain route-write authority merely because it shares
  route vocabulary.

## Fold Candidate Policy

The similarity gate may recommend a shared-kernel or branch-fold review, but it
does not authorize production contraction by itself. A state-writing fold still
needs the downstream route named in the report, such as Model-Test Alignment,
Architecture Reduction, ModelMesh, StructureMesh, or conformance replay.

Known-bad sanity cases prove that the gate rejects:

- missing sibling test paths;
- stale model-signature evidence;
- missing current similarity evidence;
- state-writing branch folds without replay evidence.
