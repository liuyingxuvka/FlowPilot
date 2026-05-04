# FlowPilot Skill Backup 20260504-130014

This directory preserves the installed `flowpilot` skill snapshot taken before
the packet-gated controller experiment.

From the repository root, use it to roll the installed skill back:

```powershell
$backup = Resolve-Path ".\backups\flowpilot-20260504-130014"
$target = Join-Path $env:USERPROFILE ".codex\skills\flowpilot"
Get-ChildItem -LiteralPath $backup -Exclude BACKUP_MANIFEST.json,README.md |
  Copy-Item -Destination $target -Recurse -Force
```

From the repository root, use it to roll the repository skill source back:

```powershell
$backup = Resolve-Path ".\backups\flowpilot-20260504-130014"
$target = Resolve-Path ".\skills\flowpilot"
Get-ChildItem -LiteralPath $backup -Exclude BACKUP_MANIFEST.json,README.md |
  Copy-Item -Destination $target -Recurse -Force
```

The `.zip` next to this directory is the same backup in archived form.
