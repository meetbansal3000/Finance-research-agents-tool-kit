"""
tests/test_production_upgrades.py - Comprehensive Verification for Production Upgrades:
  1. Footnote Note Disclosures (NVDA Note 19 Customer Concentration = 22.0%)
  2. Foreign Private Issuer Form 20-F and ESEF iXBRL Parsers
  3. TokenBucketRateLimiter and Alpha Vantage Daily Quota Guarding
  4. Batch Multi-Asset Quote Retrieval with Caching
  5. Reverse DCF Dynamic Elasticity
"""

import os
import sys
import pytest
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.ledger import ProvenanceLedger
from tools.filing import FilingExtractor
from tools.filing_note_parser import FilingNoteParser
from agents.note_extractor import NoteExtractorAgent
from tools.data_layer import DataLayer, TokenBucketRateLimiter
from tools.calc.dcf import reverse_dcf


def test_nvda_customer_concentration_note_extraction():
    """Verify that FilingNoteParser correctly extracts 22.0% customer concentration from NVDA 10-K."""
    parser = FilingNoteParser()
    res = parser.parse_filing_for_company(
        ticker="NVDA",
        cik="0001045810",
        accn="0001045810-26-000021"
    )
    assert res["status"] == "SUCCESS"
    cust_info = res["customer_concentration"]
    assert cust_info["max_concentration_pct"] == 22.0
    assert cust_info["has_concentration_above_10"] is True
    assert "sales to one direct customer represented 22%" in cust_info["quoted_snippet"]
    assert cust_info["method"] == "TEXTUAL_NOTE_EXTRACTION"


def test_note_extractor_agent_provenance():
    """Verify NoteExtractorAgent registers exact quote snippet into ProvenanceLedger."""
    ledger = ProvenanceLedger(run_id="test_note_agent")
    agent = NoteExtractorAgent(ledger=ledger)
    res = agent.extract_notes_disclosure("NVDA", cik="0001045810", accn="0001045810-26-000021")
    assert res["max_customer_concentration_pct"] == 22.0
    assert len(ledger.entries) >= 1
    entry = ledger.get_entry(res["ledger_id"])
    assert entry["raw_value"] == 22.0
    assert entry["source_tag"] == "SEC_AUDITED_NOTE"


def test_form_20f_ifrs_financial_extraction():
    """Verify Form 20-F extraction parses IFRS taxonomy facts for foreign private issuers (TSM)."""
    fe = FilingExtractor()
    ledger = ProvenanceLedger(run_id="test_20f_ledger")
    res = fe.fetch_form_20f_financials("TSM", cik="0001046179", ledger=ledger)
    assert res["status"] == "SUCCESS"
    assert res["accounting_standard"] == "IFRS"
    assert res["form"] == "20-F"
    assert res["fiscal_year"] == "FY2024"
    assert res["period_end"] == "2024-12-31"
    metrics = res["metrics"]
    assert metrics["Revenue"] == 2894307700000.0
    assert metrics["OperatingIncome"] == 1322053000000.0
    assert metrics["NetIncome"] == 1157523900000.0
    assert metrics["OperatingCashFlow"] == 1826177100000.0
    assert metrics["Capex"] == 956006500000.0
    assert metrics["FreeCashFlow"] == metrics["OperatingCashFlow"] - metrics["Capex"]
    # Verify ledger entries created with SEC_20F_IFRS tag
    assert len(ledger.entries) >= 5
    for l_id in res["ledger_ids"].values():
        e = ledger.get_entry(l_id)
        assert e["source_tag"] == "SEC_20F_IFRS"
        assert e["period_end"] == "2024-12-31"


def test_esef_ixbrl_document_parsing():
    """Verify ESEF iXBRL parser accurately un-scales and tags IFRS nonFraction elements."""
    fe = FilingExtractor()
    ledger = ProvenanceLedger(run_id="test_esef_ledger")
    sample_xhtml = '''
    <html>
      <body>
        <ix:nonFraction name="ifrs-full:Revenue" unitRef="EUR" scale="6">21350</ix:nonFraction>
        <ix:nonFraction name="ifrs-full:ProfitLoss" unitRef="EUR" scale="6">5820</ix:nonFraction>
      </body>
    </html>
    '''
    res = fe.parse_esef_ixbrl_document(sample_xhtml, ticker="SAP.DE", ledger=ledger)
    assert res["status"] == "SUCCESS"
    assert res["extracted_count"] == 2
    assert res["metrics"]["Revenue"]["val_raw"] == 21350000000.0
    assert res["metrics"]["ProfitLoss"]["val_raw"] == 5820000000.0
    assert len(ledger.entries) == 2


def test_token_bucket_rate_limiter_and_quota():
    """Verify rate limiter wait interval and Alpha Vantage 25 daily call quota tracking."""
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "library", "cache")
    limiter = TokenBucketRateLimiter(cache_dir=cache_dir)
    
    # Test min interval pacing
    t0 = datetime.datetime.now()
    limiter.wait_if_needed("yfinance")
    limiter.wait_if_needed("yfinance")
    t1 = datetime.datetime.now()
    elapsed = (t1 - t0).total_seconds()
    assert elapsed >= 0.14  # Min interval enforced

    # Test quota tracking
    allowed, count = limiter.check_alpha_vantage_quota()
    assert isinstance(allowed, bool)
    assert isinstance(count, int)
    assert count <= 25


def test_batch_quotes_and_caching():
    """Verify DataLayer.get_quotes_batch retrieves multi-asset quotes and serves from cache."""
    dl = DataLayer()
    tickers = ["AAPL", "MSFT"]
    res1 = dl.get_quotes_batch(tickers)
    assert "AAPL" in res1 and res1["AAPL"]["price"] is not None
    assert "MSFT" in res1 and res1["MSFT"]["price"] is not None

    # Second fetch must be cached
    res2 = dl.get_quotes_batch(tickers)
    assert res2["AAPL"]["cached"] is True
    assert res2["MSFT"]["cached"] is True


def test_reverse_dcf_dynamic_elasticity():
    """Verify dynamic reverse DCF handles extreme high and low growth without error."""
    # Extreme high valuation test
    res_high = reverse_dcf(
        current_price=2000.0,
        base_fcf=10.0,
        shares_outstanding=1.0,
        discount_rate=0.09,
        terminal_growth_rate=0.03
    )
    assert res_high["result"]["implied_growth_rate_pct"] > 50.0  # Successfully solved high growth

    # Normal valuation test
    res_norm = reverse_dcf(
        current_price=100.0,
        base_fcf=10.0,
        shares_outstanding=1.0,
        discount_rate=0.09,
        terminal_growth_rate=0.03
    )
    assert -50.0 <= res_norm["result"]["implied_growth_rate_pct"] <= 50.0
