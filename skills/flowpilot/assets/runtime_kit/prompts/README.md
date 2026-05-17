# FlowPilot Prompt Store

Prompt-like control text that needs to be delivered by the router lives here.
Python code should load these assets through `flowpilot_prompt_store.py` instead
of carrying long inline prompt literals.

The manifest stores content hashes so a copied runtime kit cannot silently use a
stale or partial prompt asset.
