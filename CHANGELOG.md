# Changelog

All notable changes to FlowPilot will be documented in this file.

## [0.1.0] - 2026-05-02

Initial public source release.

### Added

- Published the `flowpilot` Codex skill.
- Added reusable `.flowpilot/` project-control templates.
- Added FlowGuard-backed simulations for process, capability, startup, and release-tooling checks.
- Added install, smoke, public-release, lifecycle, heartbeat, watchdog, busy-lease, and user-flow helper scripts.
- Added bilingual README positioning FlowPilot as FlowGuard-based finite-state project control.
- Added companion skill source metadata for FlowGuard, `model-first-function-flow`, `grill-me`, `concept-led-ui-redesign`, and `frontend-design`.
- Added minimal example material under `examples/minimal/`.

### Release Notes

- This is a source release. No binary assets are included.
- FlowPilot requires the real `flowguard` Python package; it does not vendor FlowGuard.
- Companion skills are referenced by source URL, but FlowPilot release tooling does not publish companion skill repositories.
