# FlowPilot Skill Backup 20260504-130014

This directory preserves the installed `flowpilot` skill snapshot taken before
the packet-gated controller experiment.

Use it to roll the installed skill back:

```powershell
$backup = "C:\Users\liu_y\Documents\FlowGuardProjectAutopilot_20260430\backups\flowpilot-20260504-130014"
$target = "C:\Users\liu_y\.codex\skills\flowpilot"
Get-ChildItem -LiteralPath $backup -Exclude BACKUP_MANIFEST.json,README.md |
  Copy-Item -Destination $target -Recurse -Force
```

Use it to roll the repository skill source back:

```powershell
$backup = "C:\Users\liu_y\Documents\FlowGuardProjectAutopilot_20260430\backups\flowpilot-20260504-130014"
$target = "C:\Users\liu_y\Documents\FlowGuardProjectAutopilot_20260430\skills\flowpilot"
Get-ChildItem -LiteralPath $backup -Exclude BACKUP_MANIFEST.json,README.md |
  Copy-Item -Destination $target -Recurse -Force
```

The `.zip` next to this directory is the same backup in archived form.
