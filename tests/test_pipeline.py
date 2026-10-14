"""
tests/test_pipeline.py - Integration and Unit Tests for Upgrade 4 Pipeline Orchestrator
Tests:
1. Pipeline execution for US stock (AAPL).
2. Pipeline execution for Non-US stock (TCS.NS).
3. Single-round error correction when verifier encounters wrong numbers.
4. Output directory structure and artifact generation (/reports/TICKER_YYYY-MM-DD/).
"""

import os
import shutil
import pytest
from run_research import run_pipeline
from agents.analyst import AnalystAgent
from agents.verifier import ReportVerifier
from tools.ledger import ProvenanceLedger

def test_pipeline_us_stock_aapl(tmp_path):
    output_dir = str(tmp_path / "AAPL_test_run")
    result = run_pipeline(
        ticker="AAPL",
        workflow_number=1,
        output_dir=output_dir,
        perform_refetch=False
    )

    assert result["ticker"] == "AAPL"
    assert result["workflow_number"] == 1
    assert os.path.exists(result["final_report_path"])
    assert os.path.exists(result["analyst_report_path"])
    assert os.path.exists(result["skeptic_report_path"])
    assert os.path.exists(result["verification_audit_path"])

    with open(result["final_report_path"], "r", encoding="utf-8") as f:
        content = f.read()

    # Ensure structure: Verification at Top, Analyst in Middle, Skeptic at End
    idx_verif = content.find("## 🛡️ I. Verification Audit Results")
    idx_analyst = content.find("## 📊 II. Analyst Research Report")
    idx_skeptic = content.find("## 🐻 III. Skeptic Adversarial Review")

    assert idx_verif != -1, "Verification section missing from top of final report"
    assert idx_analyst != -1, "Analyst section missing from middle of final report"
    assert idx_skeptic != -1, "Skeptic section missing from end of final report"
    assert idx_verif < idx_analyst < idx_skeptic, "Report sections out of required order"

    assert result["audit_summary"]["status"] in ("PASS", "PASS WITH FLAGS")
    assert result["audit_summary"]["total_wrong"] == 0


def test_pipeline_non_us_stock_tcs(tmp_path):
    output_dir = str(tmp_path / "TCS_test_run")
    result = run_pipeline(
        ticker="TCS.NS",
        workflow_number=1,
        output_dir=output_dir,
        perform_refetch=False
    )

    assert result["ticker"] == "TCS.NS"
    assert os.path.exists(result["final_report_path"])
    assert os.path.exists(result["analyst_report_path"])
    assert os.path.exists(result["skeptic_report_path"])

    with open(result["final_report_path"], "r", encoding="utf-8") as f:
        content = f.read()

    assert "## 🛡️ I. Verification Audit Results" in content
    assert "## 📊 II. Analyst Research Report" in content
    assert "## 🐻 III. Skeptic Adversarial Review" in content
    assert "₹" in content
    assert "Crore" in content

    assert result["audit_summary"]["status"] in ("PASS", "PASS WITH FLAGS")
    assert result["audit_summary"]["total_wrong"] == 0


def test_pipeline_correction_round(tmp_path):
    """
    Test that planted wrong numbers are caught by the verifier,
    sent back to the analyst for 1 correction round, and then successfully re-verified.
    """
    test_dir = str(tmp_path / "AAPL_correction_test")
    os.makedirs(test_dir, exist_ok=True)

    # 1. Generate base analyst report
    analyst_ledger = ProvenanceLedger(run_id="test_correction_ledger")
    analyst = AnalystAgent(ledger=analyst_ledger)
    analyst_res = analyst.run_workflow(ticker="AAPL", workflow_number=1)

    rep_path = os.path.join(test_dir, "analyst_report.md")
    sidecar_path = os.path.join(test_dir, "analyst_report.provenance.json")

    # 2. Plant a deliberate wrong number into the report text
    # e.g., Replace $416,161M with $999,999M
    original_text = analyst_res["markdown_report"]
    rev_id = analyst_res["company_data"]["ledger_ids"]["revenue"]
    planted_text = original_text.replace(f"$416,161M [{rev_id}]", f"$999,999M [{rev_id}]")
    assert "$999,999M" in planted_text, "Failed to plant test error"

    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(planted_text)
    analyst_res["ledger"].save_sidecar(sidecar_path)

    # 3. Verifier checks planted report -> must catch the wrong figure
    verifier = ReportVerifier(rep_path, sidecar_path, perform_refetch=False)
    initial_audit = verifier.audit()
    assert initial_audit["summary"]["total_wrong"] >= 1, "Verifier failed to catch planted wrong number"
    assert any(w.get("ledger_id") == rev_id for w in initial_audit["wrong"])

    # 4. Analyst executes Correction Round 1
    corrected_text, updated_ledger = analyst.correct_report(
        wrong_items=initial_audit["wrong"],
        report_text=planted_text,
        ledger=analyst_res["ledger"]
    )

    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(corrected_text)
    updated_ledger.save_sidecar(sidecar_path)

    # 5. Re-audit after correction round
    re_verifier = ReportVerifier(rep_path, sidecar_path, perform_refetch=False)
    re_audit = re_verifier.audit()

    assert re_audit["summary"]["total_wrong"] == 0, f"Post-correction audit still had errors: {re_audit['wrong']}"
    assert re_audit["summary"]["status"] in ("PASS", "PASS WITH FLAGS")
