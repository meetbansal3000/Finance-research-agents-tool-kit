"""
tools/alerts.py - Regulatory Filing & Market Event Alerts Monitor (Upgrade 7)
Monitors covered securities in watchlist.txt for new SEC EDGAR filings (10-K, 10-Q, 8-K, Form 4),
material price volatility shocks (>3% move), and corporate events.
Saves structured alerts in /alerts/ and tracks state to avoid duplicate alerts.
"""

import os
import sys
import json
import urllib.request
import datetime
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import yfinance as yf
from tools.sec_cik import resolve_cik, is_us_company

ALERTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alerts")
STATE_FILE = os.path.join(ALERTS_DIR, "alerts_state.json")
LOG_FILE = os.path.join(ALERTS_DIR, "alerts_log.jsonl")
WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "watchlist.txt")


class AlertMonitor:
    def __init__(self, alerts_dir: Optional[str] = None):
        self.alerts_dir = alerts_dir or ALERTS_DIR
        os.makedirs(self.alerts_dir, exist_ok=True)
        self.state_file = os.path.join(self.alerts_dir, "alerts_state.json")
        self.log_file = os.path.join(self.alerts_dir, "alerts_log.jsonl")
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"seen_accessions": [], "last_check": None}
        return {"seen_accessions": [], "last_check": None}

    def _save_state(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def load_watchlist_tickers(self) -> List[str]:
        """Extract tickers from watchlist.txt."""
        tickers = []
        if not os.path.exists(WATCHLIST_FILE):
            return ["AAPL", "MSFT", "GOOGL", "NVDA", "TCS.NS"]
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("-")
                    ticker = parts[0].strip()
                    if ticker:
                        tickers.append(ticker)
        return tickers

    def check_sec_filings(self, ticker: str, days_lookback: int = 14) -> List[Dict[str, Any]]:
        """Check for recent SEC filings for US companies."""
        if not is_us_company(ticker):
            return []
        cik = resolve_cik(ticker)
        if not cik:
            return []

        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        user_agent = os.getenv("SEC_EDGAR_USER_AGENT", "ResearchAnalyst research@example.com")
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})

        new_alerts = []
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return []

        recent = data.get("filings", {}).get("recent", {})
        if not recent:
            return []

        accession_numbers = recent.get("accessionNumber", [])
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])

        cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days_lookback)).strftime("%Y-%m-%d")

        for i in range(min(len(accession_numbers), 20)):
            accn = accession_numbers[i]
            form = forms[i]
            f_date = filing_dates[i]
            doc_name = primary_docs[i] if i < len(primary_docs) else ""
            desc = descriptions[i] if i < len(descriptions) else ""

            if f_date < cutoff_date:
                continue

            if accn not in self.state.get("seen_accessions", []):
                severity = "HIGH" if form in ("10-K", "10-Q", "8-K") else ("MEDIUM" if form in ("4", "13F-HR") else "INFO")
                clean_accn = accn.replace("-", "")
                cik_int = int(cik)
                doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{clean_accn}/{doc_name}"

                alert = {
                    "alert_id": f"ALERT_{ticker}_{clean_accn[:10]}",
                    "ticker": ticker,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "category": "NEW_FILING",
                    "severity": severity,
                    "title": f"New SEC Form {form} Filed for {ticker}",
                    "filing_date": f_date,
                    "form": form,
                    "accession_number": accn,
                    "description": desc or f"SEC Form {form}",
                    "url": doc_url
                }
                new_alerts.append(alert)
                self.state.setdefault("seen_accessions", []).append(accn)

        return new_alerts

    def check_price_volatility(self, ticker: str, threshold_pct: float = 3.0) -> Optional[Dict[str, Any]]:
        """Check if 1-day price move exceeds threshold percentage."""
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) < 2:
                return None
            prev_close = float(hist["Close"].iloc[-2])
            last_close = float(hist["Close"].iloc[-1])
            pct_change = ((last_close - prev_close) / prev_close) * 100.0

            if abs(pct_change) >= threshold_pct:
                severity = "HIGH" if abs(pct_change) >= 5.0 else "MEDIUM"
                direction = "Surged" if pct_change > 0 else "Dropped"
                return {
                    "alert_id": f"ALERT_PRICE_{ticker}_{datetime.datetime.now().strftime('%Y%m%d')}",
                    "ticker": ticker,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "category": "PRICE_SHOCK",
                    "severity": severity,
                    "title": f"{ticker} {direction} {abs(pct_change):.2f}%",
                    "current_price": last_close,
                    "prior_close": prev_close,
                    "change_pct": round(pct_change, 2),
                    "threshold_tested": threshold_pct
                }
        except Exception:
            return None
        return None

    def run_all_checks(self, tickers: Optional[List[str]] = None, days_lookback: int = 14) -> Dict[str, Any]:
        """Execute full filing and volatility checks across watchlist."""
        target_tickers = tickers or self.load_watchlist_tickers()
        all_alerts = []

        for ticker in target_tickers:
            # 1. SEC Filing Alerts
            f_alerts = self.check_sec_filings(ticker, days_lookback=days_lookback)
            all_alerts.extend(f_alerts)

            # 2. Market Volatility Alerts
            p_alert = self.check_price_volatility(ticker, threshold_pct=3.0)
            if p_alert:
                all_alerts.append(p_alert)

        # Log alerts to jsonl
        if all_alerts:
            with open(self.log_file, "a", encoding="utf-8") as f:
                for alert in all_alerts:
                    f.write(json.dumps(alert) + "\n")

        self.state["last_check"] = datetime.datetime.now().isoformat()
        self._save_state()

        # Generate markdown report
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        report_file = os.path.join(self.alerts_dir, f"alerts_{date_str}.md")
        report_md = self._render_alerts_report(all_alerts, target_tickers)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_md)

        return {
            "date": date_str,
            "tickers_checked": target_tickers,
            "total_alerts": len(all_alerts),
            "alerts": all_alerts,
            "report_path": report_file
        }

    def _render_alerts_report(self, alerts: List[Dict[str, Any]], tickers: List[str]) -> str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"# Watchlist Event & Filing Alerts Report",
            f"**Generated:** {date_str}  ",
            f"**Watchlist Tickers Monitored:** {', '.join(tickers)}  ",
            f"**Total Active Alerts Detected:** {len(alerts)}  ",
            "",
            "---",
            ""
        ]

        if not alerts:
            lines.append("### ✅ No Critical Events Detected")
            lines.append("All covered watchlist companies trading within normal volatility bands without unacknowledged material filings.")
            return "\n".join(lines)

        lines.append("### 🚨 Active Alerts Summary")
        lines.append("| Ticker | Severity | Category | Event Title | Details / Link |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")

        for a in alerts:
            sev_badge = "🔴 **HIGH**" if a["severity"] == "HIGH" else ("🟡 **MEDIUM**" if a["severity"] == "MEDIUM" else "🟢 **INFO**")
            details = a.get("url") or f"Price Move: {a.get('change_pct')}%"
            if a.get("url"):
                details = f"[View SEC Filing]({a['url']})"
            lines.append(f"| **{a['ticker']}** | {sev_badge} | {a['category']} | {a['title']} | {details} |")

        lines.append("")
        lines.append("---")
        lines.append("*Generated by Antigravity AlertMonitor engine.*")
        return "\n".join(lines)


if __name__ == "__main__":
    monitor = AlertMonitor()
    res = monitor.run_all_checks()
    print(f"Alert check complete: {res['total_alerts']} alerts found across {len(res['tickers_checked'])} tickers.")
    print(f"Report written to: {res['report_path']}")
