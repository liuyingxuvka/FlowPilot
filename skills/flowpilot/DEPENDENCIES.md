# FlowPilot Dependency Bootstrap

FlowPilot is not complete when only the `flowpilot` skill folder is present.

Required before a formal FlowPilot run:

- `flowguard`: real Python package from `https://github.com/liuyingxuvka/FlowGuard`
- `model-first-function-flow`: Codex skill from the FlowGuard repository
- `grill-me`: Codex skill for startup and focused self-interrogation
- `flowpilot`: this skill

Recommended full-repository install:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard
python scripts\check_install.py
```

Optional UI/design companions:

- `autonomous-concept-ui-redesign`
- `frontend-design`
- `design-iterator`
- `design-implementation-reviewer`

Install optional companions only when the user wants UI/design route support:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard --include-optional
```

If a host cannot install dependencies automatically, it should report the
missing required dependency and ask the user before making heavy or global
environment changes.
