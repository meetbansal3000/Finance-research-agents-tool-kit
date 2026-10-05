"""
Comprehensive Test Suite for Verifier Agent & Provenance Ledger
Verifies:
1. Re-fetch check (source vs ledger discrepancy)
2. Cryptographic ledger integrity (tamper detection)
3. 8+ Flawed Sentences Suite (claim detection, rounding, ticker mismatch, untagged memory)
4. Strict rounding tolerances
"""

import os
import json
import pytest
from tools.ledger import ProvenanceLedger
from agents.verifier import ReportVerifier

def test_ledger_tamper_detection(tmp_path):
    """Test that manual hand-editing of ledger fields is caught by SHA-256 integrity checks."""
    ledger = ProvenanceLedger(run_id="tamper_test")
    l_id = ledger.record(
        tool="tools.calc.margin",
        inputs={"numerator": 45.0, "revenue": 100.0},
        output=45.0,
        raw_value=45.0,
        source="https://example.com",
        period="FY2025"
    )
    
    report_file = tmp_path / "tampered_report.md"
    ledger_file = tmp_path / "tampered_report.provenance.json"
    ledger.save_sidecar(str(ledger_file))
    
    # Hand-edit the saved ledger JSON behind the system's back
    with open(ledger_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["entries"][l_id]["raw_value"] = 99.0  # Tampered!
    with open(ledger_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"Gross margin was 45.0% [{l_id}].")
        
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file))
    audit_res = verifier.audit()
    
    # Verifier MUST catch the tampered ledger entry
    tampered_errors = [w for w in audit_res["wrong"] if w.get("error_type") == "LEDGER_TAMPERED"]
    assert len(tampered_errors) == 1
    assert "Cryptographic signature mismatch" in tampered_errors[0]["failure_reason"]

def test_refetch_discrepancy_detection(tmp_path):
    """Test catching when report and ledger agree with each other, but live re-fetch differs."""
    ledger = ProvenanceLedger(run_id="refetch_test")
    
    # Planted wrong number in ledger: claim YoY is 100.0% when inputs give 15.0%
    l_id = ledger.record(
        tool="tools.calc.yoy_growth",
        inputs={"current_period": 115.0, "prior_period": 100.0},
        output=100.0,
        raw_value=100.0,  # Planted wrong value!
        source="tools.calc.yoy_growth",
        period="FY2025"
    )
    
    report_file = tmp_path / "refetch_report.md"
    ledger_file = tmp_path / "refetch_report.provenance.json"
    ledger.save_sidecar(str(ledger_file))
    
    # Report agrees with planted ledger (both say 100.0%)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"Revenue grew by 100.0% [{l_id}].")
        
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file), perform_refetch=True)
    audit_res = verifier.audit()
    
    # Verifier MUST catch the discrepancy via live calculation re-fetch
    refetch_errors = [w for w in audit_res["wrong"] if w.get("error_type") == "SOURCE_REFETCH_DISCREPANCY"]
    assert len(refetch_errors) == 1
    assert refetch_errors[0]["correct_value"] == 15.0  # Live tool recomputed true value

def test_comprehensive_eight_flawed_sentences(tmp_path):
    """Test detection across 8+ diverse financial sentence types and error patterns."""
    ledger = ProvenanceLedger(run_id="eight_sentences_test")
    
    # Entry 1: AAPL Revenue = 416,161,000,000.0
    l_aapl_rev = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        inputs={"ticker": "AAPL", "concept": "us-gaap:Revenues"},
        output=416161000000.0,
        raw_value=416161000000.0,
        source="https://www.sec.gov/Archives/edgar/data/320193/0000320193-25-000079-index.html",
        period="FY2025"
    )
    
    # Entry 2: AAPL Gross Margin = 46.91%
    l_aapl_gm = ledger.record(
        tool="tools.calc.margin",
        ticker="AAPL",
        inputs={"numerator": 195201000000.0, "revenue": 416161000000.0},
        output=46.90516,
        raw_value=46.90516,
        source="https://www.sec.gov/Archives/edgar/data/320193/0000320193-25-000079-index.html",
        period="FY2025"
    )
    
    report_file = tmp_path / "multi_sentence_report.md"
    ledger_file = tmp_path / "multi_sentence_report.provenance.json"
    ledger.save_sidecar(str(ledger_file))
    
    # Construct 8+ sentences covering all test conditions
    report_lines = [
        f"1. Apple reported FY2025 total revenue of $416.2B [{l_aapl_rev}].",  # S1: Valid rounding $416.2B -> PASS
        f"2. Gross margin expanded to 46.91% [{l_aapl_gm}].",                  # S2: Valid percentage -> PASS
        "3. Operating margin collapsed to 12.5% in the fourth quarter.",        # S3: Untracked percentage -> FAIL (UNTRACKED_FIGURE)
        "4. Capital expenditures surged to $45.8B without justification.",      # S4: Untracked dollar figure -> FAIL (UNTRACKED_FIGURE)
        "5. The company's auditor is Ernst & Young LLP since 2009.",            # S5: Untagged auditor claim -> FAIL (UNTAGGED_MEMORY_CLAIM)
        "6. Apple maintains a dominant position in search and smartphones.",    # S6: Untagged market position -> FAIL (UNTAGGED_MEMORY_CLAIM)
        "7. Revenue reached $100B, and [UNVERIFIED: model memory] the founder resigned in 2011.", # S7: Mixed -> FAIL (UNTRACKED_FIGURE)
        f"8. Microsoft (MSFT) delivered record revenue of $416.2B [{l_aapl_rev}].", # S8: Valid ID but wrong ticker (MSFT vs AAPL) -> FAIL (TICKER_MISMATCH)
        f"9. Apple reported FY2025 revenue of $550.0B [{l_aapl_rev}]."         # S9: Blatant value mismatch ($550B vs $416.2B) -> FAIL (VALUE_MISMATCH)
    ]
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file))
    audit_res = verifier.audit()
    
    confirmed_lines = [c["line"] for c in audit_res["confirmed"]]
    wrong_by_line = {w["line"]: w["error_type"] for w in audit_res["wrong"]}
    unverif_errors_by_line = {}
    for u in audit_res["unverifiable"]:
        unverif_errors_by_line.setdefault(u["line"], []).append(u["error_type"])
    
    # S1 & S2 passed
    assert 1 in confirmed_lines
    assert 2 in confirmed_lines
    
    # S3: Untracked percentage caught
    assert 3 in unverif_errors_by_line and "UNTRACKED_FIGURE" in unverif_errors_by_line[3]
    
    # S4: Untracked currency caught
    assert 4 in unverif_errors_by_line and "UNTRACKED_FIGURE" in unverif_errors_by_line[4]
    
    # S5: Untagged auditor claim caught
    assert 5 in unverif_errors_by_line and "UNTAGGED_MEMORY_CLAIM" in unverif_errors_by_line[5]
    
    # S6: Untagged market position claim caught
    assert 6 in unverif_errors_by_line and "UNTAGGED_MEMORY_CLAIM" in unverif_errors_by_line[6]
    
    # S7: Untracked $100B caught in mixed sentence
    assert 7 in unverif_errors_by_line and "UNTRACKED_FIGURE" in unverif_errors_by_line[7]
    
    # S8: Ticker mismatch caught
    assert 8 in wrong_by_line and wrong_by_line[8] == "TICKER_MISMATCH"
    
    # S9: Value mismatch caught
    assert 9 in wrong_by_line and wrong_by_line[9] == "VALUE_MISMATCH"

def test_rounding_tolerance_boundaries():
    """Test exact mathematical boundary behavior of rounding tolerance checks."""
    verifier = ReportVerifier.__new__(ReportVerifier)
    
    # Currency: $416,161,000,000 vs $416.2B (diff = 0.0093% <= 0.5% -> True)
    assert verifier.verify_value_with_tolerance(416.2 * 1e9, 416161000000.0, is_ratio=False) is True
    
    # Currency: $416,161,000,000 vs $416.16B (diff = 0.0002% <= 0.5% -> True)
    assert verifier.verify_value_with_tolerance(416.16 * 1e9, 416161000000.0, is_ratio=False) is True
    
    # Currency: $416,161,000,000 vs $420.0B (diff = 0.92% > 0.5% -> False)
    assert verifier.verify_value_with_tolerance(420.0 * 1e9, 416161000000.0, is_ratio=False) is False
    
    # Ratios: 46.905% vs 46.91% (diff = 0.005 <= 0.10 -> True)
    assert verifier.verify_value_with_tolerance(46.91, 46.905, is_ratio=True) is True
    
    # Ratios: 46.905% vs 46.9% (diff = 0.005 <= 0.10 -> True)
    assert verifier.verify_value_with_tolerance(46.90, 46.905, is_ratio=True) is True
    
    # Ratios: 46.905% vs 47.5% (diff = 0.595 > 0.10 -> False)
    assert verifier.verify_value_with_tolerance(47.50, 46.905, is_ratio=True) is False
