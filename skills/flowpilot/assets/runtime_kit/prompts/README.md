# FlowPilot Prompt Store

Prompt-like control text that needs to be delivered by the router lives here.
Python code should load these assets through `flowpilot_prompt_store.py` instead
of carrying long inline prompt literals.

The manifest stores content hashes so a copied runtime kit cannot silently use a
stale or partial prompt asset.

Current prompt groups:

- `controller/` stores Controller-facing table text.
- `startup/` stores startup and resume prompt fragments.
- `cards/` stores card ACK policy fragments.
- `packets/` stores packet, result, and role-output contract fragments used by
  the packet/runtime delivery path.

When moving prompt text out of Python, add the asset here, register it in
`manifest.json`, and keep the Python side loading by prompt id through the
PromptStore. Do not add inline fallback copies for hash-managed prompt text.
