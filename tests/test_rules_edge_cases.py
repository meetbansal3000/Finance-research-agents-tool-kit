"""
Unit tests for Verifier rules and edge cases:
- Currency Mismatches
- Headings Parsing and Default-Deny Enforcement
- HTML Comments and Alt-Text Extraction
- Prohibition of numbers inside [UNVERIFIED: model memory]
- Status logic: PASS, PASS WITH FLAGS, PASS WITH FLAGS (NOT RE-FETCHED), FAIL
"""

import os
import json
import pytest
from tools.ledger import ProvenanceLedger
from agents.verifier import ReportVerifier

def test_currency_mismatch_detection(tmp_path):
    """Test that labelling an Indian Rupee (INR) figure with USD $ fails."""
    ledger = ProvenanceLedger(run_id="currency_test")
    l_inr = ledger.record(
        tool="yfinance.quote",
        ticker="TCS.NS",
        currency="INR",
        inputs={"symbol": "TCS.NS", "price": 2114.40},
        output=2114.40,
        raw_value=2114.40,
        source="NSE Quote",
        period="FY2025"
    )
    
    report_file = tmp_path / "currency_mismatch.md"
    ledger_file = tmp_path / "currency_mismatch.provenance.json"
    ledger.save_sidecar(str(ledger_file))

    # Planted currency mismatch: TCS trades at $2114.40 USD instead of ₹2114.40 INR
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"- TCS trades at $2114.40 USD [{l_inr}].")

    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file))
    audit = verifier.audit()

    assert audit["summary"]["total_wrong"] == 1
    assert audit["wrong"][0]["error_type"] == "CURRENCY_MISMATCH"
    assert audit["summary"]["status"] == "FAIL"

def test_headings_and_html_comments_enforcement(tmp_path):
    """Test that headings and HTML comments with financial claims are parsed and audited."""
    ledger = ProvenanceLedger(run_id="headings_comments_test")
    l_rev = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        currency="USD",
        inputs={"ticker": "AAPL", "concept": "us-gaap:Revenues"},
        output=416161000000.0,
        raw_value=416161000000.0,
        source="SEC 10-K",
        period="FY2025"
    )
    
    report_file = tmp_path / "headings_comments.md"
    ledger_file = tmp_path / "headings_comments.provenance.json"
    ledger.save_sidecar(str(ledger_file))

    report_text = f"""# Apple Delivered Record $416.2B Revenue in FY2025 [{l_rev}]
<!-- Competitor Android has lost significant market share in enterprise -->
![Chart showing $500M market opportunity](https://example.com/chart.png)
- Total revenue reached $416.2B [{l_rev}].
"""
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file))
    audit = verifier.audit()

    # The HTML comment contains an untagged competitor assertion
    unverif_errors = [u["error_type"] for u in audit["unverifiable"]]
    assert "UNTAGGED_MEMORY_CLAIM" in unverif_errors or "UNTAGGED_CLAIM" in unverif_errors
    # The image alt text contains an untracked $500M number
    assert "UNTRACKED_FIGURE" in unverif_errors

def test_memory_tag_prohibits_numbers(tmp_path):
    """Test that [UNVERIFIED: model memory] cannot contain numbers or percentages."""
    ledger = ProvenanceLedger(run_id="memory_tag_test")
    report_file = tmp_path / "memory_tag.md"
    ledger_file = tmp_path / "memory_tag.provenance.json"
    ledger.save_sidecar(str(ledger_file))

    report_text = """# Memory Tag Rule Test
- [UNVERIFIED: model memory] Operating profit grew 22% in the prior period.
- [UNVERIFIED: model memory] The company has an installed base of 2 billion active devices.
- [UNVERIFIED: model memory] Strong ecosystem lock-in supports customer retention.
"""
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file))
    audit = verifier.audit()

    # Lines 1 & 2 contain figures (22%, 2 billion) and MUST fail with UNTRACKED_FIGURE
    unverif = audit["unverifiable"]
    assert len(unverif) == 3
    assert unverif[0]["error_type"] == "UNTRACKED_FIGURE"
    assert unverif[1]["error_type"] == "UNTRACKED_FIGURE"
    # Line 3 has no numbers and passes as MODEL_MEMORY_TAGGED
    assert unverif[2]["error_type"] == "MODEL_MEMORY_TAGGED"
    assert audit["summary"]["status"] == "FAIL"

def test_verifier_status_logic(tmp_path):
    """Test PASS vs PASS WITH FLAGS vs FAIL."""
    ledger = ProvenanceLedger(run_id="status_logic_test")
    l1 = ledger.record(
        tool="tools.calc.yoy_growth",
        ticker="AAPL",
        inputs={"current_period": 105.0, "prior_period": 100.0},
        output=5.0,
        raw_value=5.0,
        source="tools.calc.metrics",
        period="FY2025"
    )

    # 1. Pure PASS report
    p_file = tmp_path / "pure_pass.md"
    p_sidecar = tmp_path / "pure_pass.provenance.json"
    with open(p_file, "w", encoding="utf-8") as f:
        f.write(f"- Revenue grew 5.0% [{l1}].\n")
    ledger.save_sidecar(str(p_sidecar))

    v1 = ReportVerifier(report_path=str(p_file), ledger_path=str(p_sidecar))
    a1 = v1.audit()
    assert a1["summary"]["status"] == "PASS"

    # 2. PASS WITH FLAGS (tagged memory claim, no numbers)
    pwf_file = tmp_path / "pass_with_flags.md"
    pwf_sidecar = tmp_path / "pass_with_flags.provenance.json"
    with open(pwf_file, "w", encoding="utf-8") as f:
        f.write(f"- Revenue grew 5.0% [{l1}].\n- [UNVERIFIED: model memory] Strong brand reputation.\n")
    ledger.save_sidecar(str(pwf_sidecar))

    v2 = ReportVerifier(report_path=str(pwf_file), ledger_path=str(pwf_sidecar))
    a2 = v2.audit()
    assert a2["summary"]["status"] == "PASS WITH FLAGS"
