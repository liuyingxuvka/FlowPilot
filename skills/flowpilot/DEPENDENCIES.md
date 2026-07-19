# FlowPilot Dependency Bootstrap

FlowPilot is not complete when only the `flowpilot` skill folder is present.

Required before a formal FlowPilot run:

- `flowguard`: real Python package from `https://github.com/liuyingxuvka/FlowGuard`
- `flowguard`: current Codex agent skill from the FlowGuard repository
- `flowpilot`: this skill

Recommended full-repository install:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard
python scripts\check_install.py
```

Optional direct UI/design companion:

- `autonomous-concept-ui-redesign`

That child skill owns any internal UI helper composition. FlowPilot does not
list or install those internal helpers as direct dependencies.

Install optional companions only when the user wants UI/design route support:

```powershell
python scripts\install_flowpilot.py --install-missing --install-flowguard --include-optional
```

If a host cannot install dependencies automatically, it should report the
missing required dependency and ask the user before making heavy or global
environment changes.
