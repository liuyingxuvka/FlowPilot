# FlowPilot Startup Intake Desktop Preview

This folder contains the native Windows desktop prototype for the FlowPilot
startup intake dialog.

Run it from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File docs\ui\startup_intake_desktop_preview\flowpilot_startup_intake.ps1
```

The preview uses the canonical FlowPilot default icon at:

```text
assets/brand/flowpilot-icon-default.png
```

It is intentionally not wired into the FlowPilot controller, router, startup
state, packet runtime, or scheduling flow.
