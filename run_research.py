#!/usr/bin/env python3
"""
run_research.py - Autonomous Pipeline Orchestrator (Upgrade 4)
Orchestrates:
  Analyst Agent (Playbook Workflow)
    -> Verifier Agent (Audit & Re-fetch)
    -> [Conditional Correction Round 1]
    -> Skeptic Agent (Adversarial Bear Case & Sensitivity Grid)
    -> Final Synthesized Report

Usage:
    python run_research.py <ticker> [workflow_number]
    e.g. python run_research.py AAPL 1
    e.g. python run_research.py TCS.NS 1
"""

import os
import sys
import argparse
import datetime
import shutil
from typing import Dict, Any, Optional

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from tools.ledger import ProvenanceLedger
from agents.analyst import AnalystAgent
from agents.verifier import ReportVerifier
from agents.skeptic import SkepticAgent

def run_pipeline(
    ticker: str,
    workflow_number: int = 1,
    output_dir: Optional[str] = None,
    perform_refetch: bool = True,
    strict_audit: bool = False,
    enable_nvidia: bool = False
) -> Dict[str, Any]:
    """
    Execute full autonomous research pipeline for a given ticker and workflow.
    """
    ticker = ticker.strip()
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    target_dir = output_dir or os.path.join("reports", f"{ticker}_{date_str}")
    os.makedirs(target_dir, exist_ok=True)

    print(f"\n=======================================================")
    print(f"🚀 STARTING RESEARCH PIPELINE: {ticker} (Workflow {workflow_number})")
    print(f"📁 Destination Directory: {target_dir}")
    print(f"=======================================================")

    # -------------------------------------------------------------------------
    # STAGE 1: Analyst Agent
    # -------------------------------------------------------------------------
    print(f"\n[Stage 1/4] 👨‍💼 Analyst Agent: Executing Workflow {workflow_number}...")
    analyst_ledger = ProvenanceLedger(run_id=f"{ticker}_analyst_{date_str}")
    analyst = AnalystAgent(ledger=analyst_ledger)
    analyst_res = analyst.run_workflow(ticker=ticker, workflow_number=workflow_number)

    analyst_report_path = os.path.join(target_dir, "analyst_report.md")
    analyst_sidecar_path = os.path.join(target_dir, "analyst_report.provenance.json")

    with open(analyst_report_path, "w", encoding="utf-8") as f:
        f.write(analyst_res["markdown_report"])
    analyst_res["ledger"].save_sidecar(analyst_sidecar_path)
    print(f"  ✓ Analyst report written to: {analyst_report_path}")
    print(f"  ✓ Provenance ledger saved: {len(analyst_res['ledger'].entries)} entries")

    # -------------------------------------------------------------------------
    # STAGE 2: Verifier Agent & Single-Round Error Correction
    # -------------------------------------------------------------------------
    print(f"\n[Stage 2/4] 🛡️ Verifier Agent: Auditing analyst report against ledger...")
    verifier = ReportVerifier(
        report_path=analyst_report_path,
        ledger_path=analyst_sidecar_path,
        perform_refetch=perform_refetch
    )
    audit_res = verifier.audit()
    summary = audit_res["summary"]
    print(f"  Initial Audit Result: {summary['status']} ({summary['total_confirmed']} Confirmed, {summary['total_wrong']} Wrong, {summary['total_unverifiable']} Unverifiable)")

    correction_performed = False
    if summary["total_wrong"] > 0:
        print(f"\n  ⚠️ Discrepancy detected: {summary['total_wrong']} wrong figure(s) identified.")
        print(f"  🔄 Sending feedback back to Analyst Agent for Correction Round 1...")

        corrected_report_text, updated_ledger = analyst.correct_report(
            wrong_items=audit_res["wrong"],
            report_text=analyst_res["markdown_report"],
            ledger=analyst_res["ledger"]
        )

        with open(analyst_report_path, "w", encoding="utf-8") as f:
            f.write(corrected_report_text)
        updated_ledger.save_sidecar(analyst_sidecar_path)
        analyst_res["markdown_report"] = corrected_report_text
        analyst_res["ledger"] = updated_ledger
        correction_performed = True

        print(f"  ✓ Analyst completed correction round. Re-verifying...")
        verifier = ReportVerifier(
            report_path=analyst_report_path,
            ledger_path=analyst_sidecar_path,
            perform_refetch=perform_refetch
        )
        audit_res = verifier.audit()
        summary = audit_res["summary"]
        print(f"  Post-Correction Audit Result: {summary['status']} ({summary['total_confirmed']} Confirmed, {summary['total_wrong']} Wrong, {summary['total_unverifiable']} Unverifiable)")
        if summary.get("total_wrong", 0) > 0 or summary.get("status") == "FAIL" or (strict_audit and (summary.get("total_unverifiable", 0) > 0 or summary.get("status") in ("FAIL", "FLAGGED"))):
            raise RuntimeError(
                f"Institutional Hard Stop: Report audit status is {summary.get('status')} with {summary.get('total_wrong', 0)} uncorrected erroneous figure(s) and {summary.get('total_unverifiable', 0)} unverifiable items after automated single-round correction. Pipeline halted under default-deny policy."
            )
    elif summary.get("status") == "FAIL" or (strict_audit and (summary.get("total_unverifiable", 0) > 0 or summary.get("status") in ("FAIL", "FLAGGED"))):
        raise RuntimeError(
            f"Institutional Hard Stop: Initial report audit failed with status {summary.get('status')} containing {summary.get('total_unverifiable', 0)} unverifiable items. Pipeline halted under default-deny policy."
        )

    verification_audit_path = os.path.join(target_dir, "verification_audit.md")
    gen_audit_path = f"{os.path.splitext(analyst_report_path)[0]}.audit.md"
    if os.path.exists(gen_audit_path) and gen_audit_path != verification_audit_path:
        shutil.copyfile(gen_audit_path, verification_audit_path)

    # -------------------------------------------------------------------------
    # STAGE 3: Skeptic Agent
    # -------------------------------------------------------------------------
    print(f"\n[Stage 3/4] 🐻 Skeptic Agent: Executing adversarial stress-testing...")
    skeptic_ledger = ProvenanceLedger(run_id=f"{ticker}_skeptic_{date_str}")
    skeptic = SkepticAgent(ledger=skeptic_ledger)
    skeptic_res = skeptic.evaluate_thesis(**analyst_res["skeptic_inputs"], enable_nvidia=enable_nvidia)

    skeptic_report_path = os.path.join(target_dir, "skeptic_review.md")
    skeptic_sidecar_path = os.path.join(target_dir, "skeptic_review.provenance.json")

    with open(skeptic_report_path, "w", encoding="utf-8") as f:
        f.write(skeptic_res["markdown_report"])
    skeptic_res["ledger"].save_sidecar(skeptic_sidecar_path)

    sk_verifier = ReportVerifier(
        report_path=skeptic_report_path,
        ledger_path=skeptic_sidecar_path,
        perform_refetch=perform_refetch
    )
    sk_audit = sk_verifier.audit()
    print(f"  ✓ Skeptic review written to: {skeptic_report_path}")
    print(f"  ✓ Skeptic Audit: {sk_audit['summary']['status']} ({sk_audit['summary']['total_confirmed']} Confirmed)")
    print(f"  ✓ Adversarial Thesis Verdict: {skeptic_res['verdict']}")
    if sk_audit["summary"].get("total_wrong", 0) > 0 or sk_audit["summary"].get("status") == "FAIL" or (strict_audit and (sk_audit["summary"].get("total_unverifiable", 0) > 0 or sk_audit["summary"].get("status") in ("FAIL", "FLAGGED"))):
        raise RuntimeError(
            f"Institutional Hard Stop: Skeptic report failed audit with status {sk_audit['summary'].get('status')} ({sk_audit['summary'].get('total_wrong', 0)} wrong, {sk_audit['summary'].get('total_unverifiable', 0)} unverifiable). Pipeline halted under default-deny policy."
        )

    # -------------------------------------------------------------------------
    # STAGE 4: Final Synthesized Report
    # -------------------------------------------------------------------------
    print(f"\n[Stage 4/4] 📑 Synthesizing Final Comprehensive Research Dossier...")
    final_report_path = os.path.join(target_dir, "final_report.md")

    final_content = _build_final_synthesized_report(
        ticker=ticker,
        workflow_number=workflow_number,
        date_str=date_str,
        audit_res=audit_res,
        correction_performed=correction_performed,
        analyst_markdown=analyst_res["markdown_report"],
        skeptic_res=skeptic_res,
        sk_audit=sk_audit
    )

    with open(final_report_path, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"  ✓ Final Report successfully synthesized: {final_report_path}")
    print(f"\n=======================================================")
    print(f"✅ PIPELINE COMPLETE FOR {ticker}!")
    print(f"Overall Status: {audit_res['summary']['status']} (Analyst) | {sk_audit['summary']['status']} (Skeptic)")
    print(f"All artifacts saved in: {target_dir}")
    print(f"=======================================================\n")

    return {
        "ticker": ticker,
        "workflow_number": workflow_number,
        "target_dir": target_dir,
        "final_report_path": final_report_path,
        "analyst_report_path": analyst_report_path,
        "skeptic_report_path": skeptic_report_path,
        "verification_audit_path": verification_audit_path,
        "audit_summary": audit_res["summary"],
        "skeptic_audit_summary": sk_audit["summary"],
        "skeptic_verdict": skeptic_res["verdict"],
        "correction_performed": correction_performed
    }

def _build_final_synthesized_report(
    ticker: str,
    workflow_number: int,
    date_str: str,
    audit_res: Dict[str, Any],
    correction_performed: bool,
    analyst_markdown: str,
    skeptic_res: Dict[str, Any],
    sk_audit: Dict[str, Any]
) -> str:
    """
    Construct the final unified report containing:
    1. Top: Verification Audit results (status, what failed, what could not be checked, reconciliations).
    2. Middle: Analyst Agent's research work.
    3. End: Skeptic Agent's adversarial bear case & sensitivity grid.
    """
    summary = audit_res["summary"]
    reconciliations = audit_res.get("reconciliations", [])
    wrong_items = audit_res.get("wrong", [])
    unverifiable_items = audit_res.get("unverifiable", [])

    # Format what failed
    what_failed_md = ""
    if wrong_items:
        what_failed_md += "#### ❌ Discrepancies / Failed Figures\n"
        for item in wrong_items:
            what_failed_md += f"- **[Line {item.get('line', 'N/A')}] [{item.get('ledger_id', 'N/A')}]**: {item.get('claim')}\n  - Reason: {item.get('failure_reason', 'Figure does not match source or ledger.')}\n"
    else:
        what_failed_md += "_None. Zero numerical discrepancies identified across audited financial statements and calculations._\n"

    # Format what could not be checked
    what_could_not_be_checked_md = ""
    if unverifiable_items:
        what_could_not_be_checked_md += "#### ⚠️ Unverified Claims & Unchecked Elements\n"
        for item in unverifiable_items:
            what_could_not_be_checked_md += f"- **[Line {item.get('line', 'N/A')}] [{item.get('error_type', 'UNVERIFIED')}]**: {item.get('claim')}\n  - *Detail:* {item.get('reason')}\n"
    else:
        what_could_not_be_checked_md += "_None. All assertions backed by primary sources._\n"

    # Format reconciliations
    reconciliations_md = ""
    if reconciliations:
        reconciliations_md += "\n#### ⚖️ Reported Headline vs Statutory Reconciliations\n"
        reconciliations_md += "| Metric | Derived / Statutory | Company Headline | Delta | Status | Explanation |\n"
        reconciliations_md += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for rec in reconciliations:
            reconciliations_md += f"| {rec['metric']} | `{rec['derived_val']}` [{rec['derived_id']}] | `{rec['headline_val']}` [{rec['headline_id']}] | {rec['delta']:+.2f} | **{rec['status']}** | {rec['explanation']} |\n"

    correction_note = "✅ **None Required** (Initial draft passed all numerical verifications)."
    if correction_performed:
        correction_note = "⚠️ **Correction Round 1 Executed** (Discrepancies identified on initial pass were successfully repaired by Analyst Agent)."

    final_md = f"""# Comprehensive Research Dossier: {ticker}
**Workflow:** Playbook Workflow {workflow_number}  
**Dossier Date:** {date_str}  
**Generated By:** Antigravity Autonomous Research Orchestrator  
**Audit Status:** **{summary['status']}**  

---

## 🛡️ I. Verification Audit Results (Top Section)

> **Audit Status:** **{summary['status']}**  
> **Figures Confirmed:** {summary['total_confirmed']} | **Wrong Figures:** {summary['total_wrong']} | **Unverified Flags:** {summary['total_unverifiable']}  
> **Correction Round:** {correction_note}  

### 1. What Failed
{what_failed_md}

### 2. What Could Not Be Checked / Audited
{what_could_not_be_checked_md}
{reconciliations_md}

---

## 📊 II. Analyst Research Report (Middle Section)

{analyst_markdown}

---

## 🐻 III. Skeptic Adversarial Review (End Section)

> **Adversarial Verdict:** **{skeptic_res['verdict']}**  
> **Skeptic Verifier Status:** **{sk_audit['summary']['status']}** ({sk_audit['summary']['total_confirmed']} Confirmed Claims)  

{skeptic_res['markdown_report']}

---
*Autonomous research pipeline completed. All assertions and stress models anchored in Provenance Ledger records.*
"""
    return final_md

def main():
    parser = argparse.ArgumentParser(description="Antigravity Autonomous Research Pipeline Orchestrator")
    parser.add_argument("ticker", type=str, help="Ticker symbol (e.g. AAPL, TCS.NS, MSFT)")
    parser.add_argument("workflow", type=int, nargs="?", default=1, help="Playbook workflow number (default: 1)")
    parser.add_argument("--no-refetch", action="store_true", help="Disable live network re-fetch in Verifier")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory")
    parser.add_argument("--enable-nvidia", action="store_true", help="Enable NVIDIA NIM hardware accelerated adversarial stress-testing")

    args = parser.parse_args()
    run_pipeline(
        ticker=args.ticker,
        workflow_number=args.workflow,
        output_dir=args.output_dir,
        perform_refetch=not args.no_refetch,
        enable_nvidia=args.enable_nvidia
    )

if __name__ == "__main__":
    main()
