# Dependency Sources

## Required

- Python package: `flowguard`
- Codex skill: `model-first-function-flow`
- Codex skill: `flowpilot`

## FlowGuard Source

FlowPilot requires the real `flowguard` package in the active Python
environment. The package source can be local or remote, but the runtime import
must succeed before model-backed work begins.

Agents may document or override the source with:

```text
FLOWGUARD_REPO_URL
FLOWGUARD_SKILL_SOURCE
```

## Verification

The minimum runtime check is:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
```

The minimum skill check is to confirm the `model-first-function-flow` skill is
installed and readable.

## Installation Philosophy

v1 should not implement a full installer. It should provide an AI-agent-readable
installation contract and self-check scripts. The agent that installs the
project is responsible for satisfying missing dependencies according to this
contract.
