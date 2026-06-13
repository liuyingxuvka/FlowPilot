# Design

## Single Gate

FlowPilot will dynamically compute a same-family repair loop review whenever a
semantic blocker is about to receive an ordinary PM repair packet.

If the family has more than five attempts, the runtime will stop issuing the
ordinary PM repair packet and return a control-plane break-glass duty. The
break-glass path then decides whether to return to normal flow, repair the
control plane, enter Recovery Supervisor, or stop for the user.

## Family Computation

Use existing blocker metadata:

- normalized route node id, with route versions and repeated repair suffixes
  removed;
- blocker class;
- gate kind;
- required recheck role.

The computation deliberately avoids packet id as the primary family key because
each repair iteration creates new packets.

## Runtime Boundary

The runtime owns the mechanical threshold and foreground duty projection. It
does not read sealed packet/result bodies and does not decide whether the
project work is good. It only decides that ordinary repair has looped too many
times to remain trusted.

## Prompt Boundary

PM may not select another ordinary repair when the runtime reports the threshold
is exceeded. Controller uses the existing break-glass playbook. FlowGuard
Operator treats new packets and route versions as insufficient unless there is
a real new information delta or a loop escape.

## Evidence Boundary

FlowGuard models prove the expected control-flow shape. Runtime tests prove the
threshold is enforced and under-threshold repair still works. Card coverage
tests prove the guidance is present.
