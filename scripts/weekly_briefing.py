"""
scripts/weekly_briefing.py - Standalone Entry Point for Weekly Market & Watchlist Briefing
Generates multi-timeframe performance, macroeconomic overview, and thesis tracking for watchlist.txt.
Saves output to reports/weekly_briefing_<YYYYMMDD>.md.
"""

import os
import sys
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.briefing import WeeklyBriefingGenerator

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def main():
    print("=" * 60)
    print("🗓️ GENERATING ANTIGRAVITY WEEKLY WATCHLIST BRIEFING")
    print("=" * 60)
    generator = WeeklyBriefingGenerator()
    report_file = generator.generate_briefing()

    print(f"\n✅ Weekly Briefing generated successfully!")
    print(f"📄 Output saved to: {report_file}")
    if os.path.exists(report_file):
        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"📊 Report Length: {len(content):,} characters\n")


if __name__ == "__main__":
    main()
