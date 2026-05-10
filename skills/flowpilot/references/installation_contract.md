# Installation Contract

FlowPilot requires:

- real `flowguard` Python package from
  `https://github.com/liuyingxuvka/FlowGuard`;
- installed/readable `model-first-function-flow` skill;
- installed/readable `grill-me` skill;
- this `flowpilot` skill;
- installer-readable dependency metadata in `flowpilot.dependencies.json`;
- writable project workspace for `.flowpilot/`;
- Python available on `PATH` for checks and task-local models.

Minimum runtime check:

```powershell
python scripts/install_flowpilot.py --check
python scripts/audit_local_install_sync.py
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python scripts/check_install.py
```

Expected result:

- FlowGuard import succeeds;
- schema version is reported;
- `flowpilot.dependencies.json` parses;
- `skills/flowpilot/SKILL.md` exists and declares `name: flowpilot`;
- repo-owned installed skills report `source_fresh: true`, meaning the
  installed Codex skill content matches the repository source rather than only
  existing on disk;
- template and simulation files exist;
- project-control files under `.flowpilot/current.json`,
  `.flowpilot/index.json`, and `.flowpilot/runs/<run-id>/` exist.

If dependencies are missing, the installing agent should connect the real
FlowGuard source before using this skill. Do not create a local mini-framework
or bypass the dependency check.

## Installer Entry Point

For Codex-compatible hosts, the standard installer entry is:

```powershell
python scripts/install_flowpilot.py --install-missing --install-flowguard
python scripts/check_install.py
```

The installer:

- prints the required and optional dependency tiers before reporting status;
- installs or checks `skills/flowpilot/`;
- checks the real `flowguard` Python package;
- installs missing FlowGuard from its public GitHub source only when
  `--install-flowguard` explicitly authorizes Python environment changes;
- checks required and optional companion Codex skills from
  `flowpilot.dependencies.json`;
- reports host-specific capabilities such as `raster_image_generation`;
- skips already installed skills by default;
- reports repo-owned installed skills as stale when their content digest differs
  from the repository source;
- refuses to overwrite system skills;
- installs missing GitHub-backed required skills only when their manifest source
  is explicit;
- reports missing optional companions as warnings unless the user explicitly
  requests companion installation with `--include-optional`.

If a companion skill has no public source in the manifest, the installer reports
that dependency as missing-source instead of guessing or publishing anything.

Use `--force` when intentionally refreshing a repository-owned installed skill
from the current checkout:

```powershell
python scripts/install_flowpilot.py --install-missing --force --json
```

Use `--sync-repo-owned` for the safer normal refresh path. It updates missing
or stale repository-owned skills from the current checkout without installing
optional GitHub companion skills by default:

```powershell
python scripts/install_flowpilot.py --sync-repo-owned --json
python scripts/audit_local_install_sync.py --json
```

Without `--force`, an already installed but stale repo-owned skill remains
installed and the check reports it as not ok; FlowPilot must not describe that
state as ready.

Use `--include-optional` only when the user wants the installer to fetch
optional companion skills as well as required dependencies.

If FlowGuard is missing and `--install-flowguard` is not present, the installer
must report the exact command needed instead of describing FlowPilot as ready.
The public FlowGuard source install path is:

```powershell
git clone https://github.com/liuyingxuvka/FlowGuard.git
cd FlowGuard
python -m pip install -e .
python -m flowguard schema-version
```

Host-specific capabilities are not hard-coded by skill name. Codex may satisfy
`raster_image_generation` with the built-in `imagegen` skill. Another host may
use a differently named tool or command, as long as the route records provider
identity and evidence before the visual gate runs. If no provider exists, the
visual gate is blocked or explicitly waived by the correct role.

## Public Release Preflight

Before publishing this repository, run:

```powershell
python scripts/check_public_release.py
```

The release preflight checks this FlowPilot repository only. It scans tracked
files for private runtime state and secret-shaped content, checks the dependency
manifest, checks external dependency `SKILL.md` links when URLs are available,
and runs the configured validation commands. It never commits, tags, pushes,
packages, uploads, or releases companion skill repositories.

## Automatic Installation Policy

FlowPilot may automatically install missing project-local tools and libraries
when all of these are true:

- the dependency is needed for the active route node, current chunk, checks, or
  implementation;
- the install is local to the project or active virtual environment;
- it does not require secrets, payment, private accounts, or global system
  changes;
- it is reversible by normal project dependency cleanup;
- the agent records the command and verification result.

Startup should write a dependency plan and install only the minimum tooling
needed to run FlowPilot and current model checks. Future route, chunk, UI,
native-build, or packaging dependencies should be recorded as `deferred` until
their node or verification command is active.

Ask the user before heavy, global, system-wide, paid, private-account,
destructive, or irreversible installation work.

User approval permits the install when it becomes necessary. It does not mean
all approved tools should be installed at startup.

FlowPilot v1 intentionally avoids being a standalone package manager. That does
not prohibit automatic dependency installation during a project run.
