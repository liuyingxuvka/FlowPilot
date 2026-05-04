param(
  [Parameter(Mandatory = $true)]
  [string]$TaskName,

  [string]$ProjectRoot = (Resolve-Path ".").Path,
  [int]$IntervalMinutes = 2,
  [int]$StaleMinutes = 5,
  [string]$HeartbeatAutomationId = "",
  [string]$PythonPath = "",
  [switch]$Status,
  [switch]$Disable,
  [switch]$Unregister
)

$ErrorActionPreference = "Stop"

function ConvertTo-TaskStatus {
  param([string]$Name)
  $task = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  if (-not $task) {
    return [pscustomobject]@{
      task_name = $Name
      exists = $false
      state = "missing"
    }
  }
  $info = Get-ScheduledTaskInfo -TaskName $Name
  return [pscustomobject]@{
    task_name = $task.TaskName
    exists = $true
    state = $task.State.ToString()
    enabled = $task.Settings.Enabled
    hidden = $task.Settings.Hidden
    last_run_time = $info.LastRunTime
    next_run_time = $info.NextRunTime
    last_task_result = $info.LastTaskResult
    principal_user = $task.Principal.UserId
    logon_type = $task.Principal.LogonType.ToString()
    run_level = $task.Principal.RunLevel.ToString()
    actions = @($task.Actions | ForEach-Object { ($_.Execute + " " + $_.Arguments).Trim() })
  }
}

function Quote-Arg {
  param([string]$Value)
  return '"' + ($Value -replace '"', '\"') + '"'
}

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

if ($Status) {
  ConvertTo-TaskStatus -Name $TaskName | ConvertTo-Json -Depth 6
  exit 0
}

if ($Disable) {
  $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if ($existing) {
    if ($existing.State -eq "Running") {
      Stop-ScheduledTask -TaskName $TaskName
    }
    Disable-ScheduledTask -TaskName $TaskName | Out-Null
  }
  ConvertTo-TaskStatus -Name $TaskName | ConvertTo-Json -Depth 6
  exit 0
}

if ($Unregister) {
  $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if ($existing) {
    if ($existing.State -eq "Running") {
      Stop-ScheduledTask -TaskName $TaskName
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  }
  ConvertTo-TaskStatus -Name $TaskName | ConvertTo-Json -Depth 6
  exit 0
}

if (-not $PythonPath) {
  $pythonw = Get-Command "pythonw.exe" -ErrorAction SilentlyContinue
  if ($pythonw) {
    $PythonPath = $pythonw.Source
  } else {
    $python = Get-Command "python.exe" -ErrorAction Stop
    $PythonPath = $python.Source
  }
}

$scriptPath = Join-Path $ProjectRoot "scripts\flowpilot_watchdog.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
  throw "flowpilot_watchdog.py not found under $ProjectRoot"
}

$watchdogArgs = @(
  (Quote-Arg $scriptPath),
  "--root", (Quote-Arg $ProjectRoot),
  "--stale-minutes", "$StaleMinutes",
  "--watchdog-automation-id", (Quote-Arg $TaskName),
  "--watchdog-automation-kind", "windows_task_scheduler",
  "--watchdog-created-with-heartbeat",
  "--watchdog-automation-active",
  "--watchdog-hidden-noninteractive",
  "--json"
)

if ($HeartbeatAutomationId) {
  $watchdogArgs += @("--automation-id", (Quote-Arg $HeartbeatAutomationId))
}

if ([System.IO.Path]::GetFileName($PythonPath).ToLowerInvariant() -eq "pythonw.exe") {
  $action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument ($watchdogArgs -join " ") `
    -WorkingDirectory $ProjectRoot
} else {
  $command = @(
    "Set-Location -LiteralPath $(Quote-Arg $ProjectRoot);",
    "& $(Quote-Arg $PythonPath) $($watchdogArgs -join ' ') | Out-Null"
  ) -join " "
  $action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -Command $([string](Quote-Arg $command))" `
    -WorkingDirectory $ProjectRoot
}

$trigger = New-ScheduledTaskTrigger `
  -Once `
  -At (Get-Date).AddMinutes(1) `
  -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
  -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
  -Hidden `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

$principal = New-ScheduledTaskPrincipal `
  -UserId $env:USERNAME `
  -LogonType Interactive `
  -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
  if ($existing.State -eq "Running") {
    Stop-ScheduledTask -TaskName $TaskName
  }
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Principal $principal `
  -Description "FlowPilot external watchdog. Hidden/noninteractive task; disable or unregister before heartbeat shutdown." | Out-Null

ConvertTo-TaskStatus -Name $TaskName | ConvertTo-Json -Depth 6
