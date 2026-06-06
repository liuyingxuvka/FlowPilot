# Design

## Parent Field Contracts

`simulations/flowpilot_field_contract_model.py` owns the critical field list.
It records the owner, validator, required value, and transition unlocked by each
critical field. Current background collaboration fields use
`host_liveness_status`, `liveness_decision`, `role_binding_mode`, and current
run binding fields; old liveness or fixed-role fields are modeled only as
hazards.

## Child Field Mesh

`simulations/flowpilot_field_mesh_model.py` owns the parent/child topology. The
runner scans source files and assigns every observed field to one child model
and one importance tier. Critical fields must be seen in code and their
validator must be present.

## Entry And Install Binding

The split `flowpilot_new_*` modules are implementation children. Public role
handoff commands continue to name the single public entrypoint
`flowpilot_new.py`, and install checks must require every child module needed by
that entrypoint.
