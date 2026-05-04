# Changelog

## 0.2.0 - 2026-05-04

### Added

- Added the native Windows-oriented FlowPilot Cockpit package with a live route/task view, multi-task tabs, English/Chinese UI strings, settings, and support entry.
- Added `scripts/audit_local_install_sync.py` to verify repository-owned installed skills are source-fresh, installed skill names are not duplicated, and Cockpit source files are tracked before release.
- Added a `VERSION` file so release checks and documentation have a single current version marker.
- Added autonomous UI design rules for native desktop screenshot verification, concept/resource traceability, and real app icon realization checks.

### Changed

- Updated FlowPilot startup protocol from three questions to four by adding a display-surface choice: open Cockpit UI or continue with chat route signs.
- Updated the installer with `--sync-repo-owned` so repository-owned skills can be refreshed without pulling optional companion skills by default.
- Tightened release modeling so local install sync, duplicate installed skill names, and tracked Cockpit source are release gates.

### Fixed

- Made optional companion skill availability warning-only unless explicitly requested for installation.
- Removed stale release-version references and local absolute path leakage from release-facing documentation.

## 0.1.0 - 2026-05-02

### Added

- Initial public FlowPilot skill package, templates, FlowGuard models, install checks, examples, and documentation.
