"""
tests/test_universal_sec_research.py
Tests universal SEC EDGAR CIK resolution, dynamic financial fact extraction for any US company,
Skeptic inventory materiality threshold, and uncapped multi-source pipeline execution.
"""

import pytest
from tools.sec_cik import SecCikResolver, resolve_cik, resolve_company_name, is_us_company
from agents.analyst import AnalystAgent
from agents.verifier import ReportVerifier
from agents.skeptic import SkepticAgent
from tools.ledger import ProvenanceLedger

def test_sec_cik_resolver():
    """Verify that SecCikResolver resolves arbitrary US tickers to valid 10-digit CIKs."""
    resolver = SecCikResolver()
    assert resolver.total_count() >= 10000

    test_cases = {
        "NVDA": "0001045810",
        "AAPL": "0000320193",
        "MSFT": "0000789019",
        "AMZN": "0001018724",
        "GOOGL": "0001652044",
        "META": "0001326801",
        "TSLA": "0001318605",
        "JNJ": "0000200406"
    }

    for ticker, expected_cik in test_cases.items():
        assert resolve_cik(ticker) == expected_cik
        assert is_us_company(ticker) is True
        assert len(resolve_company_name(ticker)) > 0

    # Non-US company should return None
    assert resolve_cik("TCS.NS") is None
    assert is_us_company("TCS.NS") is False

def test_skeptic_inventory_materiality_check():
    """Verify that Skeptic marks inventory divergence as PASS when inventories are <2% of revenue."""
    ledger = ProvenanceLedger(run_id="test_inventory_materiality")
    skeptic = SkepticAgent(ledger=ledger)

    # Software / cloud company scenario:
    # Revenue = $100B, Inventories = $500M (0.5% of revenue).
    # Inventories jump +50% (from $333M to $500M), revenue grew +10%.
    # Unadjusted divergence = +40 pp.
    # Materiality rule should classify this as PASS (Immaterial: <2% of revenue).
    wcd = {
        "rec_curr": 10000000000.0,
        "rec_prev": 9000000000.0,
        "rev_curr": 100000000000.0,
        "rev_prev": 90000000000.0,
        "inv_curr": 500000000.0,
        "inv_prev": 333333333.0
    }

    res = skeptic.evaluate_thesis(
        ticker="TEST_CLOUD",
        current_price=150.0,
        shares_outstanding=1000000000.0,
        base_fcf=20000000000.0,
        base_operating_margin=0.30,
        stated_growth_rate=0.08,
        receivables_growth_yoy=0.11,
        inventory_growth_yoy=0.50,
        revenue_growth_yoy=0.11,
        short_term_debt=1000000000.0,
        cash_and_equivalents=25000000000.0,
        total_debt=5000000000.0,
        net_debt=-20000000000.0,
        working_capital_details=wcd,
        max_customer_concentration_pct=0.0
    )

    inv_check = [r for r in res["checklist"] if r[0] == "Inventory Divergence"]
    assert len(inv_check) == 1
    # Check that status is PASS due to materiality
    assert inv_check[0][3] == "PASS"
    assert "Immaterial: <2% of revenue" in inv_check[0][1]

def test_universal_sec_verifier_refetch():
    """Verify that ReportVerifier can re-fetch facts for any US ticker using SecCikResolver."""
    verifier = ReportVerifier.__new__(ReportVerifier)
    
    # Test NVDA revenue re-fetch directly from SEC EDGAR
    entry = {
        "tool": "edgar.get_facts",
        "inputs": {"ticker": "NVDA", "concept": "us-gaap:Revenues", "period_end": "2026-01-25", "form": "10-K"},
        "raw_value": 215938000000.0
    }
    passed, live_val, info = verifier.refetch_source(entry)
    assert passed is True
    assert live_val == 215938000000.0
    assert "0001045810" in info

def test_nvda_end_to_end_research():
    """Verify that AnalystAgent can run full research workflow on NVDA via universal SEC extractor."""
    ledger = ProvenanceLedger(run_id="test_nvda_run")
    analyst = AnalystAgent(ledger=ledger)
    res = analyst.run_workflow(ticker="NVDA", workflow_number=1)

    assert res["ticker"] == "NVDA"
    assert res["company_data"]["currency"] == "USD"
    # Revenue should be > $200B (FY2026 $215.9B)
    assert res["company_data"]["revenue"] > 200000000000.0
    assert res["company_data"]["operating_income"] > 100000000000.0
    assert len(analyst.ledger.entries) >= 15
    assert "[LEDGER_" in res["markdown_report"]

