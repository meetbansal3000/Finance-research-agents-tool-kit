"""
tools/journal.py - Investment Decision Journal & Portfolio Review Engine (Upgrade 9)
Enforces disciplined investment tracking by recording investment theses, entry/exit prices,
catalysts, downside stop-losses, and retrospective post-mortem reviews.
Maintains /journal/journal.csv and renders markdown reviews in /journal/.
"""

import os
import sys
import csv
import datetime
from typing import Dict, Any, List, Optional
import yfinance as yf

JOURNAL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "journal")
CSV_PATH = os.path.join(JOURNAL_DIR, "journal.csv")
ENTRIES_DIR = os.path.join(JOURNAL_DIR, "entries")

CSV_HEADERS = [
    "decision_id", "date", "ticker", "action", "entry_price",
    "target_price", "stop_loss", "conviction", "status",
    "exit_date", "exit_price", "return_pct", "thesis", "risks"
]


class DecisionJournal:
    def __init__(self, journal_dir: Optional[str] = None):
        self.journal_dir = journal_dir or JOURNAL_DIR
        self.csv_path = os.path.join(self.journal_dir, "journal.csv")
        self.entries_dir = os.path.join(self.journal_dir, "entries")
        os.makedirs(self.journal_dir, exist_ok=True)
        os.makedirs(self.entries_dir, exist_ok=True)
        self._init_csv()

    def _init_csv(self):
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)

    def log_decision(
        self,
        ticker: str,
        action: str,
        entry_price: float,
        target_price: float,
        stop_loss: float,
        thesis: str,
        risks: str,
        conviction: str = "HIGH",
        date: Optional[str] = None
    ) -> str:
        """Record an investment decision into the journal."""
        date_str = date or datetime.datetime.now().strftime("%Y-%m-%d")
        existing = self.list_decisions()
        decision_id = f"DEC_{len(existing) + 1:04d}"

        row = [
            decision_id, date_str, ticker.upper().strip(), action.upper().strip(),
            f"{entry_price:.2f}", f"{target_price:.2f}", f"{stop_loss:.2f}",
            conviction.upper().strip(), "OPEN", "", "", "",
            thesis.strip(), risks.strip()
        ]

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        # Write detailed individual entry file
        entry_file = os.path.join(self.entries_dir, f"{decision_id}_{ticker.upper()}.md")
        content = f"""# Investment Decision Entry: {decision_id}
**Ticker:** {ticker.upper()}  
**Action:** {action.upper()}  
**Date:** {date_str}  
**Conviction:** {conviction.upper()}  
**Status:** OPEN  

---

### Price Parameters
- **Entry Price:** ${entry_price:,.2f}
- **Target Price:** ${target_price:,.2f} (Upside: {((target_price - entry_price) / entry_price)*100:+.2f}%)
- **Stop-Loss Level:** ${stop_loss:,.2f} (Max Downside Risk: {((stop_loss - entry_price) / entry_price)*100:+.2f}%)

---

### Core Investment Thesis
{thesis}

---

### Key Risks & Invalidation Catalysts
{risks}
"""
        with open(entry_file, "w", encoding="utf-8") as f:
            f.write(content)

        return decision_id

    def list_decisions(self) -> List[Dict[str, Any]]:
        """List all entries from journal.csv."""
        if not os.path.exists(self.csv_path):
            return []
        items = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(row)
        return items

    def close_decision(
        self,
        decision_id: str,
        exit_price: float,
        post_mortem_notes: str,
        exit_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Close an existing decision with exit price and post-mortem evaluation."""
        date_str = exit_date or datetime.datetime.now().strftime("%Y-%m-%d")
        decisions = self.list_decisions()
        target = None
        for d in decisions:
            if d["decision_id"] == decision_id:
                target = d
                break

        if not target:
            raise ValueError(f"Decision ID {decision_id} not found in journal.")

        entry_p = float(target["entry_price"])
        ret_pct = ((exit_price - entry_p) / entry_p) * 100.0

        target["status"] = "CLOSED"
        target["exit_date"] = date_str
        target["exit_price"] = f"{exit_price:.2f}"
        target["return_pct"] = f"{ret_pct:+.2f}%"

        # Re-write CSV
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerows(decisions)

        # Append post-mortem to markdown entry
        entry_file = os.path.join(self.entries_dir, f"{decision_id}_{target['ticker']}.md")
        if os.path.exists(entry_file):
            with open(entry_file, "a", encoding="utf-8") as f:
                f.write(f"\n---\n\n### Post-Mortem Review (Closed {date_str})\n")
                f.write(f"- **Exit Price:** ${exit_price:,.2f}\n")
                f.write(f"- **Realized Return:** {ret_pct:+.2f}%\n")
                f.write(f"- **Outcome & Lessons Learned:** {post_mortem_notes}\n")

        return target

    def generate_review_summary(self) -> str:
        """Generate comprehensive portfolio decision review report."""
        decisions = self.list_decisions()
        report_path = os.path.join(self.journal_dir, "portfolio_review.md")

        lines = [
            "# Investment Decision Journal & Portfolio Review",
            f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Total Logged Decisions:** {len(decisions)}  ",
            "",
            "---",
            "",
            "### 📋 Decisions Registry",
            "| ID | Date | Ticker | Action | Entry | Target | Stop | Conviction | Status | Realized Ret |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        for d in decisions:
            lines.append(
                f"| {d['decision_id']} | {d['date']} | **{d['ticker']}** | {d['action']} | "
                f"${float(d['entry_price']):,.2f} | ${float(d['target_price']):,.2f} | ${float(d['stop_loss']):,.2f} | "
                f"{d['conviction']} | **{d['status']}** | {d['return_pct'] or 'N/A'} |"
            )

        lines.append("")
        lines.append("---")
        lines.append("*Generated by Antigravity Decision Journal Engine.*")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return report_path


if __name__ == "__main__":
    journal = DecisionJournal()
    # Sample initial entry if empty
    if not journal.list_decisions():
        journal.log_decision(
            ticker="GOOGL",
            action="BUY",
            entry_price=347.68,
            target_price=420.00,
            stop_loss=275.00,
            thesis="Dominant advertising monopoly with $78.3B net cash cushion and accelerating Google Cloud enterprise operating leverage.",
            risks="Antitrust regulatory remedies and rising AI infrastructure capital expenditure drag on near-term FCF.",
            conviction="HIGH"
        )
    p_path = journal.generate_review_summary()
    print(f"Decision journal initialized. Review generated: {p_path}")
