# PowerShell script to create a Windows Task Scheduler job
# Runs auto release sync every 6 hours automatically

$TaskName = "WaqasAutomation_ReleaseSync"
$ScriptPath = "D:\Jugaro-Dola-Automation-1\scripts\auto_release_sync.py"
$PythonExe = "py"  # Uses default Python launcher
$ProjectRoot = "D:\Jugaro-Dola-Automation-1"

# Create the task action
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "$ScriptPath" `
    -WorkingDirectory $ProjectRoot

# Create the task trigger (every 6 hours)
$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 6) `
    -RepetitionDuration (New-TimeSpan -Days 365)

# Register the task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -RunLevel Highest `
    -Force `
    -Description "Automatically syncs GitHub releases to Supabase for auto-update system"

Write-Host "✅ Task scheduled! Release sync will run every 6 hours automatically."
Write-Host "   Task Name: $TaskName"
