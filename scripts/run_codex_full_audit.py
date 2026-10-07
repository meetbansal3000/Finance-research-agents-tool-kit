"""
scripts/run_codex_full_audit.py - Run Full System Audit & Use-Case Verification using OpenAI Codex CLI
Dispatches a deep audit prompt to Codex CLI via CodexBridge to verify:
  1. Financial Calculation Engine (DCF, Reverse DCF elasticity, WACC)
  2. Data Layer, Caching, Token-Bucket Rate Limiter & Alpha Vantage 25-call quota guard
  3. SEC EDGAR Form 10-K, Form 20-F (IFRS) and Footnote Note Extraction (NVDA Note 19)
  4. Multi-Agent Topology (Analyst, Verifier, Skeptic, NoteExtractor) & Provenance Ledger
  5. Interactive Dashboard (Streamlit) & Scheduler Automation
  6. Overall Production Readiness & Scoring
Saves the full audit report to reports/codex_audit_report.md.
"""

import os
import sys
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from tools.codex_bridge import CodexBridge
from tools.ledger import ProvenanceLedger

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

AUDIT_PROMPT = """
You are acting as an independent senior software and financial engineering auditor.
TASK DIRECTIVE: Produce the full markdown audit report right now. Do not reply with an acknowledgment or conversational question. Do not ask what to work on. Your entire response must be the final markdown audit report.

Audit Scope:
1. Financial Calculation Engine (`tools/calc/dcf.py`):
   - DCF formula, terminal value calculation, equity value per share.
   - Reverse DCF adaptive bracket elasticity for extreme high and low growth valuations.
2. Data Layer & Rate Limiting (`tools/data_layer.py`):
   - Cascading data source hierarchy (DiskCache -> yfinance -> Finnhub -> FMP -> Alpha Vantage).
   - TokenBucketRateLimiter inter-request pacing.
   - Alpha Vantage daily quota tracking (25 calls/day limit persisted to disk).
   - Batch quote fetching (`get_quotes_batch`) using fast_info.
3. Filing Ingestion & Note Extraction (`tools/filing.py`, `tools/filing_note_parser.py`, `agents/note_extractor.py`):
   - US Form 10-K extraction (AAPL, MSFT, NVDA).
   - Foreign private issuer Form 20-F extraction under ifrs-full taxonomy (TSM) with period and accession integrity.
   - ESEF iXBRL parser for European filings.
   - Textual note disclosure parser extracting customer concentration percentages (e.g. NVDA Note 19 = 22.0%).
4. Multi-Agent Architecture (`agents/analyst.py`, `agents/verifier.py`, `agents/skeptic.py`, `tools/ledger.py`):
   - Immutable ProvenanceLedger [LEDGER_XXXX] recording.
   - Independent dual verification code paths.
   - Skeptic red-team checks (customer concentration, working capital divergence, inventory buildup).
5. User Interface & Automation (`dashboard.py`, `scripts/setup_scheduler.py`, `scripts/weekly_briefing.py`):
   - Streamlit terminal layout and features.
   - OS-native task scheduler and crontab generation.

Your response must be a formatted markdown report containing:
## 1. Executive Summary
## 2. Verification of Core Use Cases
## 3. Architecture & Code Quality Assessment
## 4. Red Flags & Gaps Audit
## 5. Final Score (1 to 10) & Production Recommendation
"""


def is_substantive_audit_report(text: str) -> bool:
    if not text or len(text.strip()) < 500:
        return False
    lower = text.lower()
    # Explicitly reject conversational responses or acknowledgments
    if "what would you like me to work on" in lower or "what would you like to work on" in lower:
        return False
    # Validate presence of actual audit report sections
    return "executive summary" in lower and ("score" in lower or "audit" in lower)


def main():
    print("=" * 70)
    print("🤖 STARTING FULL SYSTEM AUDIT VIA OPENAI CODEX CLI")
    print("=" * 70)
    print("Connecting to Codex CLI on host system...")

    ledger = ProvenanceLedger(run_id="codex_system_audit")
    bridge = CodexBridge()

    print("Dispatching comprehensive audit instructions to Codex...")
    res = bridge.execute(
        prompt=AUDIT_PROMPT,
        sandbox="read-only",
        timeout=300,
        ledger=ledger
    )

    if not res["success"]:
        print(f"❌ Codex audit failed: {res.get('error')}")
        sys.exit(1)

    raw_response = res.get("response", "").strip()

    if not is_substantive_audit_report(raw_response):
        print("⚠️ Initial response was conversational acknowledgment. Re-dispatching with strict directive...")
        strict_prompt = (
            "TASK: Generate the complete markdown audit report now covering DCF, DataLayer, Filings, Multi-Agent, and Score. "
            "Do NOT ask what to work on. Begin immediately with '## 1. Executive Summary':\n\n" + AUDIT_PROMPT
        )
        res = bridge.execute(
            prompt=strict_prompt,
            sandbox="read-only",
            timeout=300,
            ledger=ledger
        )
        if not res["success"]:
            print(f"❌ Codex audit retry execution failed: {res.get('error')}")
            sys.exit(1)

        raw_response = res.get("response", "").strip()
        if not is_substantive_audit_report(raw_response):
            print(f"❌ Codex response lacked expected audit substance and required sections:\n{raw_response[:300]}")
            sys.exit(1)

    print("\n✅ Codex audit completed successfully!")
    print(f"Elapsed Time: {res.get('elapsed_seconds')}s")

    report_content = f"""# Independent Code & Use-Case Audit Report (OpenAI Codex)
**Generated:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Auditor Engine:** OpenAI Codex CLI (Model: {res.get('model', 'ChatGPT-Connected')})  
**Session ID:** `{res.get('session_id', 'N/A')}`  
**Provenance Ledger ID:** `[{res.get('ledger_id', 'N/A')}]`  

---

{raw_response}
"""

    report_path = os.path.join(REPORTS_DIR, "codex_audit_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"📄 Full audit report saved to: {report_path}\n")
    print("=" * 70)
    print("AUDIT SUMMARY PREVIEW:")
    print("=" * 70)
    print(res.get("response", "")[:1200] + "\n...")


if __name__ == "__main__":
    main()
