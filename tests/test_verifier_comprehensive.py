"""
Comprehensive Test Suite for Verifier Agent & Provenance Ledger
Verifies:
1. Re-fetch check (source vs ledger discrepancy)
2. Cryptographic HMAC ledger integrity (tamper detection)
3. 10 Prompt sentences (a) to (j) under default-deny
4. 10 New Hold-Out sentences in different style
5. Precision-aware half-unit rounding tolerance boundaries
"""

import os
import json
import pytest
from tools.ledger import ProvenanceLedger
from agents.verifier import ReportVerifier

def test_ledger_tamper_detection(tmp_path):
    """Test that manual hand-editing of ledger fields is caught by cryptographic HMAC integrity checks."""
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
    assert "Cryptographic HMAC signature mismatch" in tampered_errors[0]["failure_reason"]

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
    assert refetch_errors[0]["correct_value"] == 15.0

def test_prompt_ten_sentences_audit(tmp_path):
    """Test the 10 benchmark sentences (a) to (j) from the user prompt."""
    ledger = ProvenanceLedger(run_id="ten_prompt_sentences")
    
    # LEDGER_0001: AAPL FY2025 Revenue = 416,161,000,000.0
    l1 = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        inputs={"ticker": "AAPL", "concept": "us-gaap:Revenues"},
        output=416161000000.0,
        raw_value=416161000000.0,
        source="SEC 10-K",
        period="FY2025"
    )
    
    # LEDGER_0002: AAPL Gross Margin = 46.91%
    l2 = ledger.record(
        tool="tools.calc.margin",
        ticker="AAPL",
        inputs={"numerator": 195201000000.0, "revenue": 416161000000.0},
        output=46.90516,
        raw_value=46.90516,
        source="SEC 10-K",
        period="FY2025"
    )
    
    report_file = tmp_path / "prompt_ten.md"
    ledger_file = tmp_path / "prompt_ten.provenance.json"
    ledger.save_sidecar(str(ledger_file))
    
    report_lines = [
        "Apple's revenue grew about six percent last year.",                         # (a) Word number 'six percent' -> UNTRACKED_FIGURE
        "Net income was 93.7 billion dollars.",                                     # (b) Words '93.7 billion dollars' -> UNTRACKED_FIGURE
        f"Apple reported FY2024 revenue of $416.2B [{l1}].",                        # (c) FY2024 vs FY2025 -> PERIOD_MISMATCH
        "The audit committee changed auditors in 2023.",                            # (d) Auditor claim -> UNTAGGED_MEMORY_CLAIM
        "Samsung has been losing share to Apple in premium phones.",                # (e) Competitor/share claim -> UNTAGGED_MEMORY_CLAIM
        f"Gross margin was 46.9% [{l2}], and services margin is above 70%.",        # (f) 70% untracked -> UNTRACKED_FIGURE
        f"Revenue rose 4% year over year [{l1}].",                                  # (g) Growth claim against level ledger -> METRIC_TYPE_MISMATCH
        "The iPhone is the largest contributor to Apple's profit.",                 # (h) Untagged narrative assertion -> UNTAGGED_MEMORY_CLAIM
        "| Capex | 12,715 |",                                                       # (i) Table cell bare number -> UNTRACKED_FIGURE
        "Management expects a stronger December quarter. [ledger_0001]"             # (j) Lowercase citation syntax -> MALFORMED_CITATION
    ]
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file))
    audit = verifier.audit()
    
    unverif_errors = {u["line"]: u["error_type"] for u in audit["unverifiable"]}
    wrong_errors = {w["line"]: w["error_type"] for w in audit["wrong"]}
    
    # (a) Caught: line 1
    assert 1 in unverif_errors and unverif_errors[1] == "UNTRACKED_FIGURE"
    # (b) Caught: line 2
    assert 2 in unverif_errors and unverif_errors[2] == "UNTRACKED_FIGURE"
    # (c) Caught: line 3 (PERIOD_MISMATCH)
    assert 3 in wrong_errors and wrong_errors[3] == "PERIOD_MISMATCH"
    # (d) Caught: line 4 (UNTAGGED_MEMORY_CLAIM)
    assert 4 in unverif_errors and unverif_errors[4] == "UNTAGGED_MEMORY_CLAIM"
    # (e) Caught: line 5 (UNTAGGED_MEMORY_CLAIM)
    assert 5 in unverif_errors and unverif_errors[5] == "UNTAGGED_MEMORY_CLAIM"
    # (f) Caught: line 6 (UNTRACKED_FIGURE for 70%)
    assert 6 in unverif_errors and unverif_errors[6] == "UNTRACKED_FIGURE"
    # (g) Caught: line 7 (METRIC_TYPE_MISMATCH)
    assert 7 in wrong_errors and wrong_errors[7] == "METRIC_TYPE_MISMATCH"
    # (h) Caught: line 8 (UNTAGGED_MEMORY_CLAIM)
    assert 8 in unverif_errors and unverif_errors[8] == "UNTAGGED_MEMORY_CLAIM"
    # (i) Caught: line 9 (UNTRACKED_FIGURE in table row)
    assert 9 in unverif_errors and unverif_errors[9] == "UNTRACKED_FIGURE"
    # (j) Caught: line 10 (MALFORMED_CITATION)
    assert 10 in unverif_errors and unverif_errors[10] == "MALFORMED_CITATION"

def test_holdout_ten_sentences_audit(tmp_path):
    """Test 10 new hold-out test sentences in a different linguistic and structural style."""
    ledger = ProvenanceLedger(run_id="holdout_ten_sentences")
    
    l_cfo = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        inputs={"ticker": "AAPL", "concept": "us-gaap:NetCashProvidedByUsedInOperatingActivities"},
        output=118300000000.0,
        raw_value=118300000000.0,
        source="SEC 10-K",
        period="FY2025"
    )
    
    l_eps = ledger.record(
        tool="tools.calc.yoy_growth",
        ticker="AAPL",
        inputs={"current_period": 6.08, "prior_period": 5.43},
        output=11.97,
        raw_value=11.97,
        source="tools.calc.metrics",
        period="FY2025"
    )
    
    report_file = tmp_path / "holdout_ten.md"
    ledger_file = tmp_path / "holdout_ten.provenance.json"
    ledger.save_sidecar(str(ledger_file))
    
    holdout_lines = [
        "Apple's operating cash flow reached 118.3 billion dollars in the fiscal year.",     # 1. Spelled-out units without ID -> UNTRACKED_FIGURE
        "Diluted earnings per share increased by twelve percent year over year.",           # 2. Spelled-out words without ID -> UNTRACKED_FIGURE
        "| R&D Expense | $31,370M |",                                                       # 3. Table row with unreferenced currency value -> UNTRACKED_FIGURE
        "Tim Cook succeeded Steve Jobs as CEO in August 2011.",                             # 4. Untagged historical assertion -> UNTAGGED_CLAIM
        "The company faces intense competition from Google in mobile operating systems.",   # 5. Untagged market narrative -> UNTAGGED_MEMORY_CLAIM
        f"Total liabilities stand at $300B [{l_cfo}], while cash is $30B.",                 # 6. Mixed line with 1 valid ID and 1 unreferenced figure -> UNTRACKED_FIGURE
        f"Operating margin expanded to 31.97% [{l_cfo}].",                                  # 7. Level ledger ID cited for growth claim -> METRIC_TYPE_MISMATCH
        f"Apple reported FY2023 net income of $96.99B [{l_cfo}].",                          # 8. FY2023 vs FY2025 -> PERIOD_MISMATCH
        "Supply chain disruptions could materially impact holiday hardware shipments.",     # 9. Untagged forward-looking narrative -> UNTAGGED_CLAIM
        "Services segment generated strong recurring subscription revenues. (Ledger_0002)"  # 10. Malformed citation with parentheses -> MALFORMED_CITATION
    ]
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(holdout_lines))
        
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file))
    audit = verifier.audit()
    
    unverif_errors = {u["line"]: u["error_type"] for u in audit["unverifiable"]}
    wrong_errors = {w["line"]: w["error_type"] for w in audit["wrong"]}
    
    # 1. Caught
    assert 1 in unverif_errors and unverif_errors[1] == "UNTRACKED_FIGURE"
    # 2. Caught
    assert 2 in unverif_errors and unverif_errors[2] == "UNTRACKED_FIGURE"
    # 3. Caught
    assert 3 in unverif_errors and unverif_errors[3] == "UNTRACKED_FIGURE"
    # 4. Caught
    assert 4 in unverif_errors and unverif_errors[4] in ("UNTAGGED_CLAIM", "UNTAGGED_MEMORY_CLAIM")
    # 5. Caught
    assert 5 in unverif_errors and unverif_errors[5] == "UNTAGGED_MEMORY_CLAIM"
    # 6. Caught
    assert 6 in unverif_errors and unverif_errors[6] == "UNTRACKED_FIGURE"
    # 7. Caught
    assert 7 in wrong_errors and wrong_errors[7] == "METRIC_TYPE_MISMATCH"
    # 8. Caught
    assert 8 in wrong_errors and wrong_errors[8] == "PERIOD_MISMATCH"
    # 9. Caught
    assert 9 in unverif_errors and unverif_errors[9] in ("UNTAGGED_CLAIM", "UNTAGGED_MEMORY_CLAIM")
    # 10. Caught
    assert 10 in unverif_errors and unverif_errors[10] == "MALFORMED_CITATION"

def test_precision_aware_half_unit_tolerance():
    """Test exact half-unit rounding tolerance based on stated precision."""
    verifier = ReportVerifier.__new__(ReportVerifier)
    
    # 1. $416.2B (d=1, scale=1e9 -> unit=0.1B -> tolerance = ±$0.05B = ±$50M)
    # Raw $416,161,000,000 ($416.161B): diff is $0.039B <= $0.05B -> PASS
    passes, _, tol = verifier.verify_value_with_precision("416.2", "B", 416161000000.0)
    assert passes is True
    assert tol == 50000000.0  # 0.05B
    
    # Planted error $416.3B: diff is $0.139B > $0.05B -> FAIL
    passes, _, _ = verifier.verify_value_with_precision("416.3", "B", 416161000000.0)
    assert passes is False
    
    # 2. $416.16B (d=2, scale=1e9 -> unit=0.01B -> tolerance = ±$0.005B = ±$5M)
    # Raw $416,161,000,000 ($416.161B): diff is $0.001B <= $0.005B -> PASS
    passes, _, tol = verifier.verify_value_with_precision("416.16", "B", 416161000000.0)
    assert passes is True
    assert tol == 5000000.0  # 0.005B
    
    # 3. 46.9% (d=1, unit=0.1% -> tolerance = ±0.05%)
    # Raw 46.90516%: diff is 0.00516% <= 0.05% -> PASS
    passes, _, tol = verifier.verify_value_with_precision("46.9", "%", 46.90516, is_ratio=True)
    assert passes is True
    assert tol == 0.05
    
    # 4. 46.91% (d=2, unit=0.01% -> tolerance = ±0.005%)
    # Raw 46.90516%: diff is 0.00484% <= 0.005% -> PASS
    passes, _, tol = verifier.verify_value_with_precision("46.91", "%", 46.90516, is_ratio=True)
    assert passes is True
    assert tol == 0.005
    
    # Stated 47.0% on raw 46.90516%: diff is 0.0948% > 0.05% -> FAIL
    passes, _, _ = verifier.verify_value_with_precision("47.0", "%", 46.90516, is_ratio=True)
    assert passes is False
    
    # 5. Table row integer 12,715 (d=0, unit=1 -> tolerance = ±0.5)
    passes, _, tol = verifier.verify_value_with_precision("12,715", "", 12715.0)
    assert passes is True
    assert tol == 0.5
    passes, _, _ = verifier.verify_value_with_precision("12,715", "", 12716.0)
    assert passes is False

def test_planted_prior_year_balance_sheet_fails(tmp_path):
    """Test that planting a prior-year balance sheet value fails period integrity."""
    ledger = ProvenanceLedger(run_id="period_integrity_test")
    # Plant a prior-year FY2024 balance sheet cash value
    l_id = ledger.record(
        tool="tools.filing.extract_metric",
        ticker="AAPL",
        currency="USD",
        unit="base",
        inputs={"ticker": "AAPL", "metric": "CashAndEquivalents"},
        output=29943000000.0,
        raw_value=29943000000.0,
        source="SEC 10-K (2024-09-28)",
        period="FY2024",
        period_end="2024-09-28",
        fiscal_year="FY2024",
        notes="Planted prior-year balance sheet value"
    )
    
    rep_file = tmp_path / "aapl_fy25_report.md"
    sidecar_file = tmp_path / "aapl_fy25_report.provenance.json"
    
    # Report states FY2025, but claims prior-year value without prior qualification
    with open(rep_file, "w", encoding="utf-8") as f:
        f.write(f"# Apple Inc. (AAPL) Financial Research Report: FY2025\nCash and cash equivalents was $29,943M [{l_id}].")
    ledger.save_sidecar(str(sidecar_file))
    
    verifier = ReportVerifier(report_path=str(rep_file), ledger_path=str(sidecar_file))
    audit_res = verifier.audit()
    
    # Must fail with PERIOD_MISMATCH
    period_errors = [w for w in audit_res["wrong"] if w.get("error_type") == "PERIOD_MISMATCH"]
    assert len(period_errors) == 1
    assert "differs from report" in period_errors[0]["failure_reason"] or "Period mismatch" in period_errors[0]["failure_reason"]
    assert audit_res["summary"]["status"] == "FAIL"

def test_planted_analyst_mistake_caught_by_independent_verifier(tmp_path):
    """Test that a mistake planted in analyst extraction code is caught by independent re-fetch."""
    ledger = ProvenanceLedger(run_id="independent_refetch_test")
    # Planted mistake in analyst extraction: $450B revenue instead of audited $416.161B
    l_id = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        currency="USD",
        inputs={"ticker": "AAPL", "concept": "RevenueFromContractWithCustomerExcludingAssessedTax", "period": "FY2025", "period_end": "2025-09-27"},
        output=450000000000.0,  # Planted analyst error!
        raw_value=450000000000.0,
        source="SEC 10-K CIK0000320193",
        period="FY2025",
        period_end="2025-09-27",
        fiscal_year="FY2025"
    )
    
    rep_file = tmp_path / "aapl_planted_mistake_report.md"
    sidecar_file = tmp_path / "aapl_planted_mistake_report.provenance.json"
    
    with open(rep_file, "w", encoding="utf-8") as f:
        f.write(f"Apple FY2025 revenue was $450.0 billion [{l_id}].")
    ledger.save_sidecar(str(sidecar_file))
    
    verifier = ReportVerifier(report_path=str(rep_file), ledger_path=str(sidecar_file), perform_refetch=True)
    audit_res = verifier.audit()
    
    # The independent verifier must catch the discrepancy against the primary filing document or SEC live data!
    refetch_errors = [w for w in audit_res["wrong"] if w.get("error_type") == "SOURCE_REFETCH_DISCREPANCY"]
    assert len(refetch_errors) == 1
    assert "Live source returned" in refetch_errors[0]["failure_reason"]
    assert audit_res["summary"]["status"] == "FAIL"
