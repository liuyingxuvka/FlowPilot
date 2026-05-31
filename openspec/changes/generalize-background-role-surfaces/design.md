## Context

FlowPilot currently asks one startup option: whether background role assistance is allowed for the task. The runtime then opens only requested responsibilities through a host-supported role mechanism and records the host address as `agent_id`.

The intended product direction is not Codex-only. A host may provide a separate thread, subagent, worker, independent AI session, or another equivalent role surface. The protocol should express the portable requirement without enumerating or preferring one product's tool name.

## Goals / Non-Goals

**Goals:**

- Keep one startup authorization option.
- Use generic wording for the user-visible UI and AI-facing protocol.
- Make the AI selection rule clear: use a host-supported, isolated, addressable role surface and record the actual surface used.
- Avoid adding compatibility fields, fallback enums, or legacy translation layers.

**Non-Goals:**

- Do not hard-code Codex threads, subagents, or any other specific host product.
- Do not add a second UI choice for implementation type.
- Do not preserve old wording as an accepted current synonym when updating current protocol surfaces.

## Decisions

- Treat "background collaboration" as the user-facing concept and "host-supported isolated addressable role surface" as the AI-facing implementation contract.
- Leave the existing startup answer enum (`allow` or `single-agent`) unchanged because the user's decision is authorization, not implementation selection.
- Record implementation specificity in role-binding evidence (`agent_id` and host-surface evidence), not in the startup UI answer.

## Risks / Trade-offs

- Host-neutral wording can become too vague. Mitigation: keep the three operative adjectives in AI-facing text: host-supported, isolated, addressable.
- Some historical docs mention Codex because this repo is a Codex skill. Mitigation: update current runtime/prompt/install surfaces first; leave historical logs as history unless they are active instructions.
