"""
tests/test_period_integrity.py
Validates Period Integrity requirements under institutional audit rules:
1. Verifier must catch any figure whose period_end differs from the report's stated period_end (planting prior-year balance sheet value).
2. Apple FY2025 balance sheet net cash integrity (re-pulled from September 27, 2025 Form 10-K).
"""

import os
import pytest
from tools.ledger import ProvenanceLedger
from agents.verifier import ReportVerifier
from tools.filing import FilingExtractor

def test_planted_prior_year_balance_sheet_caught(tmp_path):
    """
    Plants prior-year September 28, 2024 cash ($29,943M) into a report stating Period End: 2025-09-27.
    Confirms verifier flags it as PERIOD_MISMATCH.
    """
    ledger = ProvenanceLedger(run_id="period_integrity_test")
    
    # Prior year cash entry planted with 2024-09-28 period_end
    l_planted = ledger.record(
        tool="tools.filing.extract_metric",
        ticker="AAPL",
        currency="USD",
        unit="base",
        inputs={"ticker": "AAPL", "metric": "CashAndEquivalents", "period_end": "2024-09-28"},
        output=29943000000.0,
        raw_value=29943000000.0,
        source="SEC Form 10-K (Accn: 0000320193-25-000079) Consolidated Balance Sheets",
        period="FY2024",
        period_end="2024-09-28",
        fiscal_year="FY2024"
    )
    
    # Valid FY2025 Revenue entry with 2025-09-27 period_end
    l_valid = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        currency="USD",
        unit="base",
        inputs={"ticker": "AAPL", "metric": "Revenue", "period_end": "2025-09-27"},
        output=416161000000.0,
        raw_value=416161000000.0,
        source="SEC Form 10-K Revenues",
        period="FY2025",
        period_end="2025-09-27",
        fiscal_year="FY2025"
    )
    
    report_content = f"""# Equity Research Report: Apple Inc. (AAPL)
**Period End: 2025-09-27**
**Fiscal Year: FY2025**

- Apple reported FY2025 revenue of $416.2 billion [{l_valid}].
- Apple holds $29,943 million in cash and cash equivalents [{l_planted}].
"""

    report_file = tmp_path / "planted_report.md"
    sidecar_file = tmp_path / "planted_report.provenance.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)
    ledger.save_sidecar(str(sidecar_file))
    
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(sidecar_file))
    audit = verifier.audit()
    
    # Assert planted prior-year value failed with PERIOD_MISMATCH
    wrong_entries = audit["wrong"]
    period_mismatches = [w for w in wrong_entries if w.get("error_type") == "PERIOD_MISMATCH" and w.get("ledger_id") == l_planted]
    assert len(period_mismatches) == 1, f"Expected PERIOD_MISMATCH on planted {l_planted}, got: {wrong_entries}"
    assert "differs from report stated period" in period_mismatches[0]["failure_reason"]
    
    # Assert valid FY2025 revenue passed
    confirmed_ids = [c.get("ledger_id") for c in audit["confirmed"]]
    assert l_valid in confirmed_ids

def test_apple_sept_27_2025_balance_sheet_net_cash():
    """
    Validates Apple September 27, 2025 audited balance sheet values:
    Cash: $35,934M, Marketable Securities Current: $18,763M, Non-Current: $77,723M -> Total Liquid: $132,420M
    Commercial Paper: $7,979M, Current Term Debt: $12,350M, Non-Current Term Debt: $78,328M -> Total Debt: $98,657M
    Net Cash: $132,420M - $98,657M = $33,763M.
    """
    fe = FilingExtractor()
    fin = fe.fetch_apple_fy25_audited_financials()
    m = fin["metrics"]
    
    assert m["CashAndEquivalents"]["val_raw"] == 35934000000.0
    assert m["ShortTermDebt"]["val_raw"] == 12350000000.0
    assert m["LongTermDebtNonCurrent"]["val_raw"] == 78328000000.0
    assert m["CommercialPaper"]["val_raw"] == 7979000000.0
    assert m["TotalCashAndMarketableSecurities"]["val_raw"] == 132420000000.0
    assert m["TotalDebt"]["val_raw"] == 98657000000.0
    assert m["NetDebt"]["val_raw"] == -33763000000.0
    assert fin["period_end"] == "2025-09-27"
    assert fin["accession_number"] == "0000320193-25-000079"
