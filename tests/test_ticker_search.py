"""
tests/test_ticker_search.py - Unit tests for company search and watchlist persistence
"""

import os
import json
import pytest
from tools.ticker_search import (
    search_company_tickers,
    lookup_primary_ticker,
    load_saved_watchlist,
    save_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    reset_watchlist,
    compute_ticker_scorecard_metrics,
    DEFAULT_WATCHLIST
)


def test_lookup_primary_ticker_known():
    assert lookup_primary_ticker("AAPL") == "AAPL"
    assert lookup_primary_ticker("msft") == "MSFT"
    assert lookup_primary_ticker("Apple") == "AAPL"
    assert lookup_primary_ticker("") is None


def test_search_company_tickers_non_empty():
    results = search_company_tickers("Tesla", max_results=3)
    assert len(results) > 0
    symbols = [r["symbol"] for r in results]
    assert "TSLA" in symbols


def test_watchlist_lifecycle(tmp_path, monkeypatch):
    test_file = str(tmp_path / "test_watchlist.json")
    monkeypatch.setattr("tools.ticker_search.WATCHLIST_FILE", test_file)

    # Initial load returns default
    wl = load_saved_watchlist()
    assert wl == DEFAULT_WATCHLIST

    # Add by company name
    ok, msg, updated = add_to_watchlist("Tesla")
    assert ok is True
    assert "TSLA" in updated

    # Duplicate check
    ok, msg, updated = add_to_watchlist("TSLA")
    assert ok is True
    assert "already in your Watchlist" in msg

    # Remove
    updated = remove_from_watchlist("TSLA")
    assert "TSLA" not in updated

    # Reset
    reset = reset_watchlist()
    assert reset == DEFAULT_WATCHLIST


def test_compute_ticker_scorecard_metrics():
    aapl_m = compute_ticker_scorecard_metrics("AAPL")
    assert aapl_m["Ticker"] == "AAPL"
    assert "31.2%" in aapl_m["Operating Margin"]
    assert aapl_m["Verdict"] == "VERIFIED BUY"
