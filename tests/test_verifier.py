"""
Unit tests for the Verifier Agent (/agents/verifier.py)
Tests audit of a deliberately flawed sample report.
"""

import os
import pytest
from tools.ledger import ProvenanceLedger
from agents.verifier import ReportVerifier

def test_verifier_catches_flaws(tmp_path):
    # 1. Create a mock provenance ledger
    ledger = ProvenanceLedger(run_id="test_audit_001")
    
    # Correct entry: Apple Revenue
    l_rev = ledger.record(
        tool="edgar.get_facts",
        inputs={"ticker": "AAPL", "concept": "us-gaap:Revenues"},
        output=416161000000.0,
        raw_value=416161000000.0,
        source="https://www.sec.gov/Archives/edgar/data/320193/0000320193-25-000079-index.html",
        form="10-K",
        period="FY2025"
    )
    
    # Entry with actual value 133,050,000,000 for Operating Income
    l_op = ledger.record(
        tool="edgar.get_facts",
        inputs={"ticker": "AAPL", "concept": "us-gaap:OperatingIncomeLoss"},
        output=133050000000.0,
        raw_value=133050000000.0,
        source="https://www.sec.gov/Archives/edgar/data/320193/0000320193-25-000079-index.html",
        form="10-K",
        period="FY2025"
    )
    
    report_file = tmp_path / "sample_flawed_report.md"
    ledger_file = tmp_path / "sample_flawed_report.provenance.json"
    
    # Save the ledger
    ledger.save_sidecar(str(ledger_file))
    
    # 2. Write sample report containing:
    # (a) One correct number: $416,161M referencing l_rev (LEDGER_0001)
    # (b) One wrong number: $250,000M referencing l_op (LEDGER_0002)
    # (c) One number with no ledger entry: $999M untracked
    # (d) One untagged memory claim: "The company was founded in a garage in Los Altos in 1976."
    report_text = f"""# Test Flawed Report
- Total Revenue in FY2025 was $416,161 Million [{l_rev}].
- Operating Income was $250,000 Million [{l_op}].
- Mysterious unverified marketing expense was $999 Million.
- The company was founded in a garage in Los Altos in 1976.
"""
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text)
        
    # 3. Run Verifier
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file))
    audit_res = verifier.audit()
    
    # 4. Assert that Verifier caught the 3 flaws and confirmed the 1 valid number:
    summary = audit_res["summary"]
    assert summary["status"] == "FAILED"
    assert summary["total_confirmed"] == 1
    assert summary["total_wrong"] == 1
    assert summary["total_unverifiable"] == 2  # 1 untracked number + 1 untagged memory claim
    
    # Check confirmed item
    assert audit_res["confirmed"][0]["ledger_id"] == l_rev
    assert "$416,161 Million" in audit_res["confirmed"][0]["claim"]
    
    # Check wrong item
    assert audit_res["wrong"][0]["ledger_id"] == l_op
    assert audit_res["wrong"][0]["error_type"] == "VALUE_MISMATCH"
    assert audit_res["wrong"][0]["correct_value"] == 133050000000.0
    
    # Check unverifiable items
    unverif_errors = [u["error_type"] for u in audit_res["unverifiable"]]
    assert "UNTRACKED_FIGURE" in unverif_errors
    assert "UNTAGGED_MEMORY_CLAIM" in unverif_errors
    
    # Check that audit report sidecar was created and original was NOT modified
    audit_md = tmp_path / "sample_flawed_report.audit.md"
    assert audit_md.exists()
    
    with open(report_file, "r", encoding="utf-8") as f:
        assert f.read() == report_text  # Original report unchanged
