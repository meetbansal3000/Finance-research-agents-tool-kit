# schedule_tasks.ps1 - Automated Windows Task Scheduler Registration
# Run this in an administrative or standard user PowerShell console

$PythonExe = "D:\AI-Workspace\finance agents for research\.venv\Scripts\python.exe"
$WorkingDir = "D:\AI-Workspace\finance agents for research"
$WeeklyScript = "D:\AI-Workspace\finance agents for research\scripts\weekly_briefing.py"
$AlertsScript = "D:\AI-Workspace\finance agents for research\tools\alerts.py"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Registering Antigravity Automated Research Schedulers..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Weekly Briefing (Every Monday at 07:00)
$WeeklyTaskName = "Antigravity_WeeklyBriefing"
$WeeklyAction = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$WeeklyScript`"" -WorkingDirectory $WorkingDir
$WeeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 07:00am
Register-ScheduledTask -TaskName $WeeklyTaskName -Action $WeeklyAction -Trigger $WeeklyTrigger -Description "Antigravity Weekly Watchlist & Macro Briefing Generator" -Force

Write-Host "[+] Task '$WeeklyTaskName' registered: Every Monday at 07:00 AM" -ForegroundColor Green

# 2. Daily Market & Filing Alerts (Every Mon-Fri at 09:00 PM)
$AlertsTaskName = "Antigravity_DailyAlerts"
$AlertsAction = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$AlertsScript`" check" -WorkingDirectory $WorkingDir
$DailyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 09:00pm
Register-ScheduledTask -TaskName $AlertsTaskName -Action $AlertsAction -Trigger $DailyTrigger -Description "Antigravity Daily Filing & Price Shock Monitor" -Force

Write-Host "[+] Task '$AlertsTaskName' registered: Mon-Fri at 09:00 PM" -ForegroundColor Green
Write-Host "`nAll Antigravity automated tasks successfully scheduled." -ForegroundColor Cyan
