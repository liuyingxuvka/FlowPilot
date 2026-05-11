# FlowPilot Contract Runtime Binding Registry Plan

Date: 2026-05-11

## Goal

Make the FlowPilot role-output contract registry the executable source of
truth for formal role outputs. A role output is valid only when one registry
entry binds the contract, runtime output type, allowed role, body schema,
default storage path, return envelope, and Router event.

This work must not be a point fix for startup activation. The startup activation
approval, repair request, and protocol dead-end decisions are the first proof
cases of the registry-driven path.

## Optimization Checklist

| # | Optimization item | Concrete change | Done condition |
|---|---|---|---|
| 1 | Add binding fields to the registry | Each runtime-backed `role_output_envelope` contract in `contract_index.json` declares `runtime_channel`, `output_type`, `body_schema_version`, `router_event`, `default_subdir`, `default_filename_prefix`, `path_key`, `hash_key`, and explicit array fields when needed. | A reviewer can read one contract row and know the exact runtime command and Router event. |
| 2 | Treat registry bindings as the runtime source | `role_output_runtime.py` builds `OUTPUT_TYPE_SPECS` from registry-backed bindings plus narrow built-in fallback metadata needed before a project registry exists. | `prepare-output --output-type <registry output_type>` works for every registry-backed role output. |
| 3 | Bind startup decisions through the same path | The three startup activation decisions are ordinary registry bindings: approval, repair request, and protocol dead-end. | They are accepted by the runtime because they are in the registry, not because of a special point patch. |
| 4 | Preserve old compatible names where already public | Existing `pm_resume_recovery_decision` remains supported as an alias for the `pm_resume_decision` contract while the registry declares the canonical binding. | Existing tests and routes using the old name still pass. |
| 5 | Constrain Router events from the registry | Source checks verify every registry-declared `router_event` exists in Router event metadata or handling code. | A typo or missing Router handler fails before runtime use. |
| 6 | Make cards cite binding rows, not guessed names | Startup and output catalog cards name the contract id, output type, and Router event for file-backed PM decisions. | A role can copy the card command without inventing a name. |
| 7 | Add exhaustive source conformance | The role-output runtime check scans the registry and runtime by `contract_id`, verifies roles/events/default paths, and parse-checks every bound output type. | Existing manual subset checks can no longer pass while registry bindings are missing. |
| 8 | Connect install check to the exhaustive check | `scripts/check_install.py` either runs the role-output runtime source check or performs equivalent exhaustive assertions. | Local install readiness fails on binding drift. |
| 9 | Sync local installed FlowPilot only after validation | Run repository tests first, then `install_flowpilot.py --sync-repo-owned --json` and local sync audit/check. | Local installed skill matches the validated repository source. |
| 10 | Stage local git only | Stage the repository changes after validation. Do not push or create a GitHub PR. | Local git has the intended files staged; remote GitHub remains untouched. |

## Bug Risk List To Model And Test

| # | Potential bug introduced by this upgrade | FlowGuard/source check must catch it |
|---|---|---|
| 1 | A contract says it is runtime-backed, but no runtime output type exists. | Registry-backed source conformance rejects missing runtime binding. |
| 2 | Runtime output type points at the wrong `contract_id`. | Source conformance compares by `contract_id`, not only by output type name. |
| 3 | Runtime allows a role not listed in the contract registry. | Source conformance compares allowed roles exactly. |
| 4 | Registry declares a Router event that Router does not handle. | Source conformance checks event existence. |
| 5 | Runtime accepts an output type that is not declared by the registry. | Source conformance reports unregistered role-output runtime specs unless explicitly marked as an alias. |
| 6 | Existing public output type aliases break, especially `pm_resume_recovery_decision`. | Alias metadata is explicit and covered by tests. |
| 7 | Startup approval becomes a special case again. | Model includes startup activation as a valid registry-backed scenario. |
| 8 | The runtime accidentally starts judging semantic quality instead of mechanics. | Existing semantic-boundary invariant remains in the FlowGuard model. |
| 9 | Controller-visible envelopes leak decision/report body fields. | Existing sealed-body and envelope-only invariants remain in the model and tests. |
| 10 | Explicit empty arrays are no longer generated or validated after registry loading. | Runtime tests and registry field checks cover explicit array metadata. |
| 11 | Cards give a command that does not match the registry row. | Card/source checks verify contract id, output type, and Router event mentions for binding-critical cards. |
| 12 | Install check passes while registry/runtime/router are out of sync. | `scripts/check_install.py` includes the exhaustive binding check. |

## FlowGuard Upgrade Requirement

Before production code edits, upgrade `simulations/flowpilot_role_output_runtime_model.py`
and `simulations/run_flowpilot_role_output_runtime_checks.py` so the model and
source scan include:

1. a valid registry-backed startup activation decision scenario;
2. hazards for missing runtime binding, wrong contract id, wrong roles, missing
   Router event, unregistered runtime output type, and broken alias support;
3. source checks that read the real registry and runtime instead of relying only
   on a hand-maintained subset.

The upgraded model must first demonstrate hazard detection, then pass on the
implemented source.

