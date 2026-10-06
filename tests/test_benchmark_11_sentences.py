"""
11 Benchmark Sentences Verification Test Suite
Tests all 11 benchmark sentences under strict default-deny and unit-level atomicity:
- Sentence 1 (PASS): Properly cited financial fact with matching ledger entry
- Sentence 2 (FAIL): Stated $416.2B [l1] with unreferenced 22% and untracked competitor claim -> Must FAIL and NOT appear in confirmed
- Sentence 3 (FAIL): Unreferenced spelled-out written word numbers ("six percent")
- Sentence 4 (FAIL): Period mismatch (stated FY2024 against FY2025 ledger record)
- Sentence 5 (FAIL): Untagged auditor claim
- Sentence 6 (FAIL): Untagged competitor / market share claim
- Sentence 7 (FAIL): Mixed line with 1 valid ID and 1 unreferenced figure (services margin 70%)
- Sentence 8 (FAIL): Metric type mismatch (growth claim cited against level ledger record)
- Sentence 9 (PASS): Properly tagged qualitative memory claim with NO numbers
- Sentence 10 (FAIL): Analysis loophole (strategic demand assertion inside [ANALYSIS] tag) -> Must FAIL and NOT appear in confirmed
- Sentence 11 (FAIL): Malformed lowercase citation syntax [ledger_0001]
"""

import os
import json
import pytest
from tools.ledger import ProvenanceLedger
from agents.verifier import ReportVerifier

def test_11_benchmark_sentences_audit(tmp_path):
    ledger = ProvenanceLedger(run_id="benchmark_11_test")
    
    # Ledger Entry 1: AAPL FY2025 Revenue = $416,161,000,000.0 USD
    l1 = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        currency="USD",
        inputs={"ticker": "AAPL", "concept": "us-gaap:Revenues", "period": "FY2025"},
        output=416161000000.0,
        raw_value=416161000000.0,
        source="https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
        period="FY2025",
        form="10-K"
    )
    
    # Ledger Entry 2: Gross Margin = 46.91%
    l2 = ledger.record(
        tool="tools.calc.margin",
        ticker="AAPL",
        currency="USD",
        inputs={"numerator": 195201000000.0, "revenue": 416161000000.0},
        output=46.90516,
        raw_value=46.90516,
        source="tools.calc.metrics.margin",
        period="FY2025"
    )
    
    # Ledger Entry 3: Implied Growth = 9.35%
    l3 = ledger.record(
        tool="tools.calc.reverse_dcf",
        ticker="AAPL",
        currency="USD",
        inputs={"current_price": 255.0, "base_fcf": 98767000000.0},
        output=9.35,
        raw_value=9.35,
        source="tools.calc.dcf.reverse_dcf",
        period="FY2025"
    )

    sentences = [
        # Sentence 1: Valid fact (PASS)
        f"Apple reported FY2025 revenue of $416.2B [{l1}].",
        
        # Sentence 2: Mixed valid + unreferenced figures & competitor claim (FAIL)
        f"Apple delivered $416.2B [{l1}], capturing 22% of smartphone volume from Samsung.",
        
        # Sentence 3: Spelled-out numbers (FAIL)
        "Apple's revenue grew about six percent last year.",
        
        # Sentence 4: Period mismatch (FAIL)
        f"Apple reported FY2024 revenue of $416.2B [{l1}].",
        
        # Sentence 5: Untagged auditor claim (FAIL)
        "The audit committee changed auditors in 2023.",
        
        # Sentence 6: Untagged competitor claim (FAIL)
        "Samsung has been losing share to Apple in premium phones.",
        
        # Sentence 7: Mixed with unreferenced figure (FAIL)
        f"Gross margin was 46.9% [{l2}], and services margin is above 70%.",
        
        # Sentence 8: Metric type mismatch (FAIL)
        f"Revenue rose 4% year over year [{l1}].",
        
        # Sentence 9: Tagged memory claim with no numbers (PASS)
        "[UNVERIFIED: model memory] Apple maintains strong developer mindshare across global software ecosystems.",
        
        # Sentence 10: Analysis Loophole with strategic demand assertion (FAIL)
        f"[ANALYSIS] The implied growth rate of 9.35% [{l3}] reflects realistic multi-year digital transformation demand.",
        
        # Sentence 11: Malformed citation syntax (FAIL)
        "Management expects a stronger December quarter. [ledger_0001]"
    ]

    report_file = tmp_path / "benchmark_11.md"
    ledger_file = tmp_path / "benchmark_11.provenance.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sentences))
    ledger.save_sidecar(str(ledger_file))

    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file))
    audit = verifier.audit()

    # Verify unit-level atomicity: S2 and S10 must NOT appear in confirmed!
    confirmed_claims = [c["claim"] for c in audit["confirmed"]]
    wrong_lines = {w["line"]: w for w in audit["wrong"]}
    unverif_lines = {u["line"]: u for u in audit["unverifiable"]}

    # Sentence 1 (Line 1): PASS
    assert any("Apple reported FY2025 revenue of $416.2B" in c for c in confirmed_claims)

    # Sentence 2 (Line 2): FAIL -> Must NOT be confirmed
    assert not any("capturing 22%" in c for c in confirmed_claims)
    assert 2 in unverif_lines
    assert unverif_lines[2]["error_type"] == "UNTRACKED_FIGURE"

    # Sentence 3 (Line 3): FAIL
    assert 3 in unverif_lines
    assert unverif_lines[3]["error_type"] == "UNTRACKED_FIGURE"

    # Sentence 4 (Line 4): FAIL (PERIOD_MISMATCH)
    assert 4 in wrong_lines
    assert wrong_lines[4]["error_type"] == "PERIOD_MISMATCH"

    # Sentence 5 (Line 5): FAIL (UNTAGGED_MEMORY_CLAIM)
    assert 5 in unverif_lines
    assert unverif_lines[5]["error_type"] == "UNTAGGED_MEMORY_CLAIM"

    # Sentence 6 (Line 6): FAIL (UNTAGGED_MEMORY_CLAIM)
    assert 6 in unverif_lines
    assert unverif_lines[6]["error_type"] == "UNTAGGED_MEMORY_CLAIM"

    # Sentence 7 (Line 7): FAIL (UNTRACKED_FIGURE)
    assert 7 in unverif_lines
    assert unverif_lines[7]["error_type"] == "UNTRACKED_FIGURE"

    # Sentence 8 (Line 8): FAIL (METRIC_TYPE_MISMATCH)
    assert 8 in wrong_lines
    assert wrong_lines[8]["error_type"] == "METRIC_TYPE_MISMATCH"

    # Sentence 9 (Line 9): PASS (MODEL_MEMORY_TAGGED)
    assert 9 in unverif_lines
    assert unverif_lines[9]["error_type"] == "MODEL_MEMORY_TAGGED"

    # Sentence 10 (Line 10): FAIL (UNTAGGED_MEMORY_CLAIM inside [ANALYSIS])
    assert not any("digital transformation demand" in c for c in confirmed_claims)
    assert 10 in unverif_lines
    assert unverif_lines[10]["error_type"] == "UNTAGGED_MEMORY_CLAIM"

    # Sentence 11 (Line 11): FAIL (MALFORMED_CITATION)
    assert 11 in unverif_lines
    assert unverif_lines[11]["error_type"] == "MALFORMED_CITATION"

    # Overall Status: FAIL due to failures in S2-S8, S10, S11
    assert audit["summary"]["status"] == "FAIL"
