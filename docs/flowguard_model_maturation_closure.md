# FlowGuard Model Maturation Closure

FlowPilot uses FlowGuard models, model-test alignment, model hierarchy, known
friction gates, and background validation artifacts before maintenance or local
install confidence is trusted. The model maturation closure gate is the final
routine check that asks whether post-evidence signals mean the model itself is
still too coarse, stale, or only scoped.

The executable gate is:

```powershell
python simulations/run_flowpilot_model_maturation_checks.py --json-out simulations/flowpilot_model_maturation_results.json
```

It calls FlowGuard `review_model_maturation_loop()` and records:

- current decision and confidence;
- unresolved maturation signals;
- required actions such as `add_state_field`, `add_transition_case`,
  `add_code_boundary_observation`, `split_child_model`, `reattach_parent_model`,
  `refresh_evidence`, or `downgrade_claim`;
- known-bad sanity checks for ACK-only closure, undisposed replacement packets,
  prompt contract gaps, stale evidence, oversized parent masking, and
  progress-only background evidence;
- singleton-vs-plural authority gaps, including duplicate daemon writers,
  duplicate active packet authorities, conflicting PM package dispositions,
  route replacement without old-object disposition, producerless repair waits,
  ACK-only semantic completion, and final progress-only closure.

The gate supports routine FlowPilot maintenance and local install confidence.
It does not replace release-level full Meta or Capability regressions when
those are required by a release or publication task.
