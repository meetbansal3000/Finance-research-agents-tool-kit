"""
scripts/setup_scheduler.py - Automated Task Scheduler Setup (Windows Task Scheduler / Cron)
Configures automated recurring execution for:
  1. Weekly Research Briefing: Every Monday at 07:00 local time (scripts/weekly_briefing.py)
  2. Daily Market Shock & SEC Filing Alerts: Monday-Friday at 21:00 local time (tools/alerts.py)
Supports:
  - Windows: Generates schedule_tasks.ps1 and registers via schtasks.exe or PowerShell ScheduledTask
  - Linux / macOS: Generates crontab snippet
"""

import os
import sys
import platform
import subprocess
import argparse

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VENV_PYTHON = os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe") if platform.system() == "Windows" else os.path.join(PROJECT_DIR, ".venv", "bin", "python")


def generate_windows_script() -> str:
    ps1_path = os.path.join(PROJECT_DIR, "scripts", "schedule_tasks.ps1")
    weekly_script = os.path.join(PROJECT_DIR, "scripts", "weekly_briefing.py")
    alerts_script = os.path.join(PROJECT_DIR, "tools", "alerts.py")

    ps1_content = f"""# schedule_tasks.ps1 - Automated Windows Task Scheduler Registration
# Run this in an administrative or standard user PowerShell console

$PythonExe = "{VENV_PYTHON}"
$WorkingDir = "{PROJECT_DIR}"
$WeeklyScript = "{weekly_script}"
$AlertsScript = "{alerts_script}"

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
"""
    with open(ps1_path, "w", encoding="utf-8") as f:
        f.write(ps1_content)
    return ps1_path


def generate_cron_snippet() -> str:
    weekly_script = os.path.join(PROJECT_DIR, "scripts", "weekly_briefing.py")
    alerts_script = os.path.join(PROJECT_DIR, "tools", "alerts.py")
    log_dir = os.path.join(PROJECT_DIR, "reports")

    cron_text = f"""# --- Antigravity Automated Financial Research Cron Jobs ---
# 1. Weekly Watchlist Briefing (Every Monday at 07:00 UTC)
0 7 * * 1 cd {PROJECT_DIR} && {VENV_PYTHON} {weekly_script} >> {log_dir}/cron_briefing.log 2>&1

# 2. Daily SEC Filing & Market Shock Alerts (Mon-Fri at 21:00 UTC)
0 21 * * 1-5 cd {PROJECT_DIR} && {VENV_PYTHON} {alerts_script} check >> {log_dir}/cron_alerts.log 2>&1
# ----------------------------------------------------------
"""
    cron_path = os.path.join(PROJECT_DIR, "scripts", "crontab.txt")
    with open(cron_path, "w", encoding="utf-8") as f:
        f.write(cron_text)
    return cron_path


def main():
    parser = argparse.ArgumentParser(description="Antigravity Automated Task Scheduler Setup")
    parser.add_argument("--install", action="store_true", help="Automatically register tasks with the operating system")
    args = parser.parse_args()

    os_type = platform.system()
    print("=" * 60)
    print(f"⏰ ANTIGRAVITY TASK SCHEDULER SETUP (OS: {os_type})")
    print("=" * 60)

    if os_type == "Windows":
        ps1_file = generate_windows_script()
        print(f"✅ Generated Windows PowerShell task registration script: {ps1_file}")
        print("\nRegistered Tasks:")
        print("  1. 'Antigravity_WeeklyBriefing' -> Every Monday at 07:00 AM")
        print("  2. 'Antigravity_DailyAlerts'    -> Mon-Fri at 09:00 PM")

        if args.install:
            print("\nExecuting registration via PowerShell...")
            res = subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ps1_file], capture_output=True, text=True)
            print(res.stdout)
            if res.returncode != 0:
                print(f"Warning: {res.stderr}")
        else:
            print("\nTo install automatically, run:")
            print(f"  .\\.venv\\Scripts\\python.exe scripts\\setup_scheduler.py --install")
            print(f"Or execute directly:")
            print(f"  powershell.exe -ExecutionPolicy Bypass -File {ps1_file}")
    else:
        cron_file = generate_cron_snippet()
        print(f"✅ Generated Crontab configuration file: {cron_file}")
        print("\nTo activate crontab:")
        print(f"  crontab -l | cat - {cron_file} | crontab -")

    print("\n✅ Task scheduler configuration complete!\n")


if __name__ == "__main__":
    main()
