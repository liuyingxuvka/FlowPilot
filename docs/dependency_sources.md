# Dependency Sources

## Required

- Python package: `flowguard`
- Codex skill: `model-first-function-flow`
- Codex skill: `flowpilot`
- Dependency manifest: `flowpilot.dependencies.json`

## Declared Public Skill Sources

FlowPilot publishes explicit source locations for required and companion
skills so installation and public-release checks do not rely on hidden local
state.

| Dependency | Source |
| --- | --- |
| `model-first-function-flow` | `https://github.com/liuyingxuvka/FlowGuard/tree/main/.agents/skills/model-first-function-flow` |
| `grill-me` | `https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me` |
| `autonomous-concept-ui-redesign` | `https://github.com/liuyingxuvka/autonomous-concept-ui-redesign-skill/tree/main/autonomous-concept-ui-redesign` |
| `frontend-design` | `https://github.com/anthropics/skills/tree/main/skills/frontend-design` |
| `design-iterator` | `https://github.com/ratacat/claude-skills/tree/main/skills/design-iterator` |
| `design-implementation-reviewer` | `https://github.com/ratacat/claude-skills/tree/main/skills/design-implementation-reviewer` |

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
python scripts/install_flowpilot.py --check
python scripts/audit_local_install_sync.py
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python scripts/check_install.py
```

The minimum skill check is to confirm the `model-first-function-flow` skill is
installed and readable.

## Installer Contract

FlowPilot uses `flowpilot.dependencies.json` as the installer-readable source of
truth. The manifest distinguishes:

- `copy_from_this_repository` for FlowPilot itself;
- `python_environment` for the real `flowguard` package;
- `github` for required or companion skills that can be installed from an
  explicit public repository path;
- `host_capabilities` for host-specific tools whose names differ across AI
  agents.

`scripts/install_flowpilot.py --install-missing` installs missing
auto-installable required skills only when the manifest has a complete source.
Optional companion skills are warning-only by default; pass
`--include-optional` when the user explicitly wants the installer to fetch
missing companions. The installer skips existing local skills by default and
does not publish or mutate companion skill repositories.

Use `scripts/install_flowpilot.py --sync-repo-owned` to refresh stale or
missing repository-owned Codex skills from the current checkout. Use
`scripts/audit_local_install_sync.py` before publishing or handoff to confirm
that repo-owned installed skills are source-fresh, installed skill names are
unique, and the legacy Cockpit prototype is absent from the active source
tree before a from-scratch UI restart.

Host-specific tools are not hard dependencies by name. For example, Codex maps
the `raster_image_generation` capability to its built-in `imagegen` skill, but
another AI agent may map the same capability to a different image-generation
tool. FlowPilot should record the provider name and check result in route
evidence before using a visual gate.

`scripts/check_public_release.py` checks whether public GitHub sources are
complete and reachable before FlowPilot is published. Missing companion skill
URLs are reported as FlowPilot release blockers until the user manually
publishes those skills or updates the dependency source.

## Installation Philosophy

v1 provides a lightweight installer and release preflight, not a general package
manager. The installer handles FlowPilot and declared missing dependencies; the
release preflight is FlowPilot-only and never uploads companion skills.
