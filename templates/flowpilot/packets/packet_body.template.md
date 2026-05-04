---
schema_version: flowpilot.packet_body.v1
packet_id: <packet-id>
run_id: <run-id>
route_id: <route-id>
node_id: <node-id>
intended_reader_role: <same-as-envelope-to_role>
body_hash_algorithm: sha256
controller_may_read: false
---

# Packet Body

This file contains the detailed work instructions for the role named by the
packet envelope `to_role`.

The controller must not read, summarize, execute, edit, or complete this body.
The controller only relays the envelope, updates holder/status, displays the
required route sign, waits for the returned envelope, and asks PM for the next
decision when blocked.

## Objective

<role-specific objective>

## Inputs

- <input-path-or-fact>

## Allowed Reads

- <path-or-source>

## Allowed Writes Or Side Effects

- <path-command-or-side-effect>

## Forbidden Actions

- <action-that-this-role-must-not-take>

## Acceptance Slice

- <bounded acceptance condition for this packet only>

## Required Verification Or Evidence

- <command-probe-screenshot-model-check-or-review-evidence>

## Return Contract

Return a `result_envelope` to the controller. Put detailed commands, files,
evidence, screenshots, findings, and unresolved issues in `result_body.md`.
