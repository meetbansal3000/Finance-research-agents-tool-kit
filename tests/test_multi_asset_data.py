"""
tests/test_multi_asset_data.py - Unit and Integration Tests for MultiAssetDataEngine (Part 1 Groundwork)
"""

import pytest
import datetime
from tools.multi_asset_data import MultiAssetDataEngine, ASSET_SPECIFICATIONS


def test_asset_specifications_integrity():
    """Verify all contracts have non-zero multipliers and initial margin specifications."""
    assert "ES=F" in ASSET_SPECIFICATIONS
    assert "CL=F" in ASSET_SPECIFICATIONS
    assert "GC=F" in ASSET_SPECIFICATIONS
    assert "BTC-USD" in ASSET_SPECIFICATIONS
    assert "VTSAX" in ASSET_SPECIFICATIONS

    es = ASSET_SPECIFICATIONS["ES=F"]
    assert es["multiplier"] == 50.0
    assert es["tick_size"] == 0.25
    assert es["initial_margin"] > 0.0

    cl = ASSET_SPECIFICATIONS["CL=F"]
    assert cl["multiplier"] == 1000.0
    assert cl["tick_value"] == 10.0


def test_futures_quotes_notional_and_leverage():
    """Verify futures quotes correctly calculate notional value and leverage ratios."""
    engine = MultiAssetDataEngine(cache_ttl_seconds=60)
    quotes = engine.get_futures_quotes(["ES=F", "CL=F", "GC=F"])

    assert len(quotes) == 3
    for q in quotes:
        assert "symbol" in q
        assert "last_price" in q
        assert q["last_price"] > 0
        assert q["notional_value"] == pytest.approx(q["last_price"] * q["multiplier"], abs=0.1)
        assert q["leverage_ratio"] > 0


def test_commodity_quotes():
    """Verify commodities return Energy and Metals with proper units."""
    engine = MultiAssetDataEngine(cache_ttl_seconds=60)
    quotes = engine.get_commodity_quotes(["CL=F", "GC=F", "HG=F"])

    assert len(quotes) == 3
    symbols = [q["symbol"] for q in quotes]
    assert "CL=F" in symbols
    assert "GC=F" in symbols
    assert "HG=F" in symbols

    for q in quotes:
        assert q["last_price"] > 0
        assert "unit" in q
        assert "category" in q


def test_crypto_perpetual_funding_rate():
    """Verify crypto spot quotes and simulated perpetual funding rate calculations."""
    engine = MultiAssetDataEngine(cache_ttl_seconds=60)
    quotes = engine.get_crypto_quotes(["BTC-USD", "ETH-USD"])

    assert len(quotes) == 2
    for q in quotes:
        assert q["last_price"] > 0
        assert "estimated_funding_rate_8h_pct" in q
        assert "estimated_funding_apr_pct" in q
        assert q["max_leverage"] >= 10


def test_treasury_yield_curve_and_spreads():
    """Verify US Treasury curve tenors and 2Y/10Y spread calculation."""
    engine = MultiAssetDataEngine(cache_ttl_seconds=60)
    yc = engine.get_treasury_yield_curve()

    assert "yield_3m" in yc
    assert "yield_10y" in yc
    assert "spread_2y_10y_bps" in yc
    assert "curve_regime" in yc
    assert len(yc["curve_points"]) == 5

    # Sanity checks on interest rates
    assert 0.0 < yc["yield_10y"] < 25.0
    assert 0.0 < yc["yield_3m"] < 25.0


def test_mutual_fund_quotes():
    """Verify mutual funds return NAV and expense ratios."""
    engine = MultiAssetDataEngine(cache_ttl_seconds=60)
    funds = engine.get_mutual_fund_quotes(["VTSAX", "FXAIX"])

    assert len(funds) == 2
    for f in funds:
        assert f["nav"] > 0
        assert "expense_ratio_pct" in f
        assert f["expense_ratio_pct"] > 0


def test_options_chain_ingestion():
    """Verify options chain pulls strikes, calls, puts, and put-call ratio."""
    engine = MultiAssetDataEngine(cache_ttl_seconds=60)
    chain = engine.get_options_chain("AAPL")

    assert chain["ticker"] == "AAPL"
    assert chain["underlying_price"] > 0
    assert len(chain["available_expirations"]) > 0
    assert chain["calls_count"] > 0
    assert chain["puts_count"] > 0
    assert chain["atm_strike"] > 0
    assert chain["put_call_ratio_oi"] > 0


def test_multi_asset_summary():
    """Verify consolidated cross-asset snapshot."""
    engine = MultiAssetDataEngine(cache_ttl_seconds=60)
    summary = engine.get_multi_asset_summary()

    assert "timestamp" in summary
    assert "treasury_curve" in summary
    assert "futures_snapshot" in summary
    assert "commodities_snapshot" in summary
    assert "crypto_snapshot" in summary
    assert "funds_snapshot" in summary
