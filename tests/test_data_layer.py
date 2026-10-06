"""
tests/test_data_layer.py - Test Suite for Multi-Source Data Layer & Fallbacks (Upgrade 6)
Tests:
1. Disk caching behavior and TTL.
2. Live quote fetching and caching with provenance ledger recording.
3. Macroeconomic series fallback (FRED / Treasury yield proxies).
4. Cascading provider fallback when primary sources fail.
5. Free-tier rate limits and regional market coverage reporting.
"""

import time
import pytest
from tools.data_layer import DataLayer, DiskCache
from tools.ledger import ProvenanceLedger

@pytest.fixture
def data_layer(tmp_path):
    layer = DataLayer()
    layer.cache = DiskCache(cache_dir=str(tmp_path / "cache"))
    return layer

def test_disk_cache_basic(tmp_path):
    cache = DiskCache(cache_dir=str(tmp_path / "test_cache"))
    cache.set("test_key", {"val": 42.0}, ttl_seconds=10)
    
    cached = cache.get("test_key")
    assert cached is not None
    assert cached["val"] == 42.0

    # Test missing key
    assert cache.get("nonexistent_key") is None

    # Test expired key
    cache.set("expired_key", {"val": 1.0}, ttl_seconds=-1)
    assert cache.get("expired_key") is None

def test_data_layer_live_quote_and_caching(data_layer):
    ledger = ProvenanceLedger(run_id="test_data_layer_run")
    
    # 1. First fetch: live
    res1 = data_layer.get_quote("AAPL", ledger=ledger)
    assert res1["price"] > 0
    assert res1["currency"] == "USD"
    assert res1["cached"] is False
    assert len(ledger.entries) == 1

    # 2. Second fetch: from cache
    res2 = data_layer.get_quote("AAPL", ledger=ledger)
    assert res2["price"] == res1["price"]
    assert res2["cached"] is True
    assert len(ledger.entries) == 2

def test_data_layer_macro_series(data_layer):
    ledger = ProvenanceLedger(run_id="test_macro_run")
    res = data_layer.get_macro_series("DGS10", ledger=ledger)
    assert res["value"] > 0
    assert "Treasury" in res["description"] or "10-Year" in res["description"]
    assert res["source"] is not None
    assert len(ledger.entries) == 1

def test_free_tier_limits_and_coverage_reports(data_layer):
    report = data_layer.get_coverage_report()
    limits = report["free_tier_limits"]
    coverage = report["market_coverage"]

    # Verify all required providers exist
    expected_providers = ["FRED", "FMP", "Finnhub", "Alpha Vantage", "yfinance", "SEC EDGAR"]
    for prov in expected_providers:
        assert prov in limits
        assert "rate_limit" in limits[prov]
        assert "daily_limit" in limits[prov]
        assert "coverage" in limits[prov]

    # Verify all regions exist
    expected_regions = ["US", "UK", "Europe", "Asia"]
    for r in expected_regions:
        assert r in coverage
        assert "primary_source" in coverage[r]
        assert "remaining_gaps" in coverage[r]

def test_cascading_fallback_on_primary_failure(data_layer, monkeypatch):
    """Test that when yfinance fails, fallback proceeds to next provider."""
    def mock_yfinance_fail(ticker):
        raise RuntimeError("Simulated yfinance outage")

    monkeypatch.setattr(data_layer, "_fetch_yfinance_quote", mock_yfinance_fail)

    # Provide a mock for Finnhub fallback
    data_layer.finnhub_key = "mock_key"
    def mock_finnhub_success(ticker):
        return {
            "ticker": ticker,
            "price": 330.50,
            "currency": "USD",
            "shares_outstanding": 15000000000.0,
            "market_cap": 4957500000000.0,
            "source": "Finnhub Mock",
            "timestamp": "2026-10-06T12:00:00"
        }
    monkeypatch.setattr(data_layer, "_fetch_finnhub_quote", mock_finnhub_success)

    ledger = ProvenanceLedger(run_id="test_fallback_run")
    res = data_layer.get_quote("AAPL", ledger=ledger)

    assert res["price"] == 330.50
    assert res["source"] == "Finnhub Mock"
    assert res["cached"] is False
    assert len(ledger.entries) == 1
