# Close FlowGuard Test Gaps

## Summary

Add ordinary test coverage for the FlowGuard coverage gaps identified by the
full model coverage inventory, then run the new tests and FlowGuard alignment
checks to expose current implementation or evidence failures.

## Motivation

The previous boundary-test pass closed only two selected model-test alignment
gaps. The full inventory shows that FlowPilot still has uncovered or
insufficiently evidenced FlowGuard areas:

- not-OK or unparsed model runners;
- missing or scoped replay adapters;
- skipped or scoped validation evidence;
- abstract model runners without detected ordinary-test references.

The goal of this change is not to make every model green by weakening checks.
It is to make the missing coverage explicit in ordinary tests, so future green
claims cannot hide untested or skipped model obligations.

## Scope

This change may add or update:

- ordinary `unittest` tests under `tests/`;
- model-test alignment evidence rows under `simulations/` when they describe
  real source/test evidence;
- coverage inventory metadata and reports;
- OpenSpec task records and FlowGuard adoption notes.

This change must not:

- mutate active `.flowpilot/runs/` state;
- change production FlowPilot behavior only to satisfy tests;
- treat skipped, scoped, unparsed, or failed evidence as passed;
- push, tag, publish, or release.

## Success Criteria

- Every gap class from the full inventory is represented in a concrete test
  plan.
- Every runner in `abstract_without_detected_ordinary_test_reference` has an
  ordinary test reference that either executes the runner, consumes its current
  result, or asserts its explicit evidence boundary.
- Missing/scoped replay adapter gaps have ordinary tests that keep the scoped
  boundary visible.
- Not-OK and unparsed runners have ordinary tests that expose their current
  failure/parse state without silently converting them to pass evidence.
- The new focused test suite is run as a group after coverage is added.
- OpenSpec strict validation and FlowGuard adoption records are updated.
