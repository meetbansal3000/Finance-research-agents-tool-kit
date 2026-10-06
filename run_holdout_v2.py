import os
import sys
import re

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from tools.ledger import ProvenanceLedger
from agents.verifier import ReportVerifier

def main():
    ledger = ProvenanceLedger(run_id="holdout_v2_run")
    
    # 5 ledger entries specified by user:
    # LEDGER_0001 = Apple FY2025 revenue, $416,161M, USD.
    # LEDGER_0002 = Apple FY2025 net income, $112,010M.
    # LEDGER_0003 = TCS FY2025 revenue, 255,324 crore, INR.
    # LEDGER_0004 = Apple FCF yield, 1.98% (a percentage).
    # LEDGER_0005 = TCS FY2025 net income, 48,553 crore, INR.
    l1 = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        currency="USD",
        inputs={"ticker": "AAPL", "metric": "Revenue", "period_end": "2025-09-27"},
        output=416161000000.0,
        raw_value=416161000000.0,
        source="SEC 10-K",
        period="FY2025"
    )
    l2 = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        currency="USD",
        inputs={"ticker": "AAPL", "metric": "NetIncome"},
        output=112010000000.0,
        raw_value=112010000000.0,
        source="SEC 10-K",
        period="FY2025"
    )
    l3 = ledger.record(
        tool="filing.financials",
        ticker="TCS.NS",
        currency="INR",
        unit="crore",
        inputs={"ticker": "TCS.NS", "metric": "Revenue"},
        output=2553240000000.0,
        raw_value=2553240000000.0,
        source="TCS FY2025 Audited Statements",
        period="FY2025"
    )
    l4 = ledger.record(
        tool="tools.calc.fcf_yield",
        ticker="AAPL",
        inputs={"free_cash_flow_val": 98767000000.0},
        output=1.98,
        raw_value=1.98,
        source="tools.calc.metrics.fcf_yield",
        period="FY2025"
    )
    l5 = ledger.record(
        tool="filing.financials",
        ticker="TCS.NS",
        currency="INR",
        unit="crore",
        inputs={"ticker": "TCS.NS", "metric": "NetIncome"},
        output=485530000000.0,
        raw_value=485530000000.0,
        source="TCS FY2025 Audited Statements",
        period="FY2025"
    )

    # Read sentences from tests/holdout_v2.txt
    sentences = []
    with open("tests/holdout_v2.txt", "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            # Match (1) ... through (10) ...
            m = re.match(r'^\s*\(\d+\)\s*(.+)$', line_str)
            if m:
                sentences.append(m.group(1))

    # Write report and sidecar to temp
    rep_file = "scratch_holdout_v2_report.md"
    sidecar_file = "scratch_holdout_v2_report.provenance.json"

    with open(rep_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sentences))
    ledger.save_sidecar(sidecar_file)

    verifier = ReportVerifier(report_path=rep_file, ledger_path=sidecar_file, perform_refetch=False)
    audit = verifier.audit()

    print("\n=======================================================")
    print("RAW OUTPUT: HOLDOUT V2 TEST (10 SENTENCES)")
    print("=======================================================")
    confirmed_by_line = {c["line"]: c for c in audit.get("confirmed", [])}
    wrong_by_line = {w["line"]: w for w in audit.get("wrong", [])}
    unverifiable_by_line = {u["line"]: u for u in audit.get("unverifiable", [])}

    for idx, s in enumerate(sentences, start=1):
        if idx in confirmed_by_line:
            c = confirmed_by_line[idx]
            status = "PASS"
            detail = f"Confirmed against {c.get('ledger_id')}"
        elif idx in wrong_by_line:
            w = wrong_by_line[idx]
            status = "FAIL"
            detail = f"Error: {w.get('failure_reason')} (Error type: {w.get('error_type', 'FAIL')})"
        elif idx in unverifiable_by_line:
            u = unverifiable_by_line[idx]
            if u.get("error_type") == "MODEL_MEMORY_TAGGED":
                status = "PASS WITH FLAGS"
                detail = "Tagged model memory claim (no unverified numbers)"
            else:
                status = "FAIL"
                detail = f"Unverifiable: {u.get('reason')} ({u.get('error_type')})"
        else:
            status = "UNKNOWN"
            detail = "No audit entry"

        print(f"({idx}) {s}")
        print(f"    --> RESULT: {status} | {detail}\n")

    print(f"OVERALL REPORT STATUS: {audit['summary']['status']}")
    print(f"SUMMARY: {audit['summary']['total_confirmed']} Confirmed, {audit['summary']['total_wrong']} Wrong, {audit['summary']['total_unverifiable']} Unverifiable\n")

    # Clean up scratch files
    try:
        os.remove(rep_file)
        os.remove(sidecar_file)
    except Exception:
        pass

if __name__ == "__main__":
    main()
