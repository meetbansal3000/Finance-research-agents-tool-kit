import pytest
from unittest.mock import patch
from tools.filing import FilingExtractor
from tools.ledger import ProvenanceLedger


def test_tcs_extractor_real_filing():
    fp = FilingExtractor()
    ledger = ProvenanceLedger(run_id="test_tcs_provenance")
    res = fp.fetch_tcs_financials(ledger=ledger)

    if res.get("status") == "data unavailable":
        pytest.skip("TCS filing document unavailable offline")

    assert res.get("status", "OK") == "OK" or "data unavailable" not in res.get("status", "")
    assert res["ticker"] == "TCS.NS"
    assert res["currency"] == "INR"
    assert res["unit"] == "crore"

    m = res["metrics"]

    # 1. Revenue
    assert m["Revenue"]["val_crore"] == 267021.0
    assert m["Revenue"]["val_raw"] == 267021.0 * 1e7
    assert "Revenue from operations 70,698 67,087 64,479 267,021 2,55,324" in m["Revenue"]["quote"]
    assert m["PriorRevenue"]["val_crore"] == 255324.0

    # 2. PBT vs Operating Income
    assert m["PBT_Before_Exceptional"]["val_crore"] == 70013.0
    assert "PROFIT BEFORE EXCEPTIONAL ITEMS AND TAX 18,362 17,469 16,402 70,013 65,331" in m["PBT_Before_Exceptional"]["quote"]
    assert m["OperatingIncome"]["val_crore"] is None
    assert m["OperatingIncome"]["val_raw"] is None
    assert "not reported separately" in m["OperatingIncome"]["quote"]

    # 3. Attributable Net Profit
    assert m["AttributableNetProfit"]["val_crore"] == 49210.0
    assert m["AttributableNetProfit"]["val_raw"] == 49210.0 * 1e7
    assert "Shareholders of the Company 13,718 10,657 12,224 49,210 48,553" in m["AttributableNetProfit"]["quote"]
    assert m["PriorAttributableNetProfit"]["val_crore"] == 48553.0

    # 4. Cash Flow & Capex
    assert m["OperatingCashFlow"]["val_crore"] == 52094.0
    assert m["PPE_Capex"]["val_crore"] == 3670.0
    assert m["Intangibles_Capex"]["val_crore"] == 408.0
    assert m["Capex"]["val_crore"] == 4078.0
    assert m["DerivedFreeCashFlow"]["val_crore"] == 48016.0
    assert m["HeadlineFreeCashFlow"]["val_crore"] is None

    # 5. Balance Sheet & Liquid Assets Breakdown
    assert m["CashAndCashEquivalents"]["val_crore"] == 6417.0
    assert m["OtherBankBalances"]["val_crore"] == 6491.0
    assert m["CurrentInvestments"]["val_crore"] == 33770.0
    assert m["TotalLiquidAssets"]["val_crore"] == 46678.0
    assert "Cash and cash equivalents 6,417 8,342" in m["CashAndCashEquivalents"]["quote"]
    assert "Other balances with banks 6,491 7,121" in m["OtherBankBalances"]["quote"]
    assert "Investments 33,770 30,689" in m["CurrentInvestments"]["quote"]

    # 6. Lease Liabilities (Extracted via regex, not typed) & Net Debt
    assert m["LeaseLiabilities_NonCurrent"]["val_crore"] == 9453.0
    assert m["LeaseLiabilities_Current"]["val_crore"] == 1830.0
    assert m["TotalDebt"]["val_crore"] == 11283.0
    assert m["NetDebt"]["val_crore"] == -35395.0
    assert "Lease liabilities 9,453 7,838" in m["LeaseLiabilities_NonCurrent"]["quote"]
    assert "Lease liabilities 1,830 1,554" in m["LeaseLiabilities_Current"]["quote"]

    # 7. Trade Receivables
    assert m["TradeReceivables"]["val_crore"] == 57729.0
    assert m["PriorTradeReceivables"]["val_crore"] == 50233.0

    # Provenance ledger checks
    assert m["Revenue"]["ledger_id"] is not None
    assert m["PBT_Before_Exceptional"]["ledger_id"] is not None
    assert m["OperatingIncome"]["ledger_id"] is None  # None values not recorded
    assert m["AttributableNetProfit"]["ledger_id"] is not None
    assert m["TotalLiquidAssets"]["ledger_id"] is not None


def test_tcs_extractor_patterns_removed_returns_no_numbers():
    """
    Feeds text with line item patterns removed/obfuscated and confirms
    no numbers come back (all numeric metrics are None, zero hardcoded fallback).
    """
    fp = FilingExtractor()

    mock_pages = [
        {
            "page_number": 1,
            "text": """
            Audited Consolidated Statement of Financial Results
            Some company description without revenue or profit lines.
            Line without numbers: General and administrative updates.
            """
        },
        {
            "page_number": 2,
            "text": """
            Audited Consolidated Balance Sheet
            General corporate capital structure.
            Total assets: unavailable.
            """
        },
        {
            "page_number": 3,
            "text": """
            Audited Consolidated Statement of Cash Flows
            Cash activities narrative without cash flow figures.
            """
        }
    ]

    mock_ext_data = {
        "doc_path": "library/filings/TCS_FY2026_Audited_Results.pdf",
        "meta": {"sha256": "fakehash", "http_status": 200, "size": 1234},
        "pages": mock_pages
    }

    with patch.object(fp, "extract_non_us_filing", return_value=(True, mock_ext_data, "OK")):
        res = fp.fetch_tcs_financials()

        assert res["ticker"] == "TCS.NS"
        metrics = res["metrics"]

        # Confirm that every single numeric metric returned is None - zero fallback numbers!
        for k, v in metrics.items():
            assert v.get("val_crore") is None, f"Metric '{k}' unexpectedly returned number {v.get('val_crore')} when pattern was removed!"
            assert v.get("val_raw") is None, f"Metric '{k}' unexpectedly returned raw number {v.get('val_raw')} when pattern was removed!"
            assert v.get("val_pct") is None, f"Metric '{k}' unexpectedly returned percentage {v.get('val_pct')} when pattern was removed!"
