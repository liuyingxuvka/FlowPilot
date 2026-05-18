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

2026-05-18 owner-module polish note: the newly split action-factory, PM
role-work, terminal-ledger, Controller receipt, and packet control-plane modules
were scanned for prompt-like text. The remaining text is runtime metadata,
schema/policy payload content, ledger summaries, or existing PromptStore call
sites, so no additional prompt asset met the criteria for safe externalization.
