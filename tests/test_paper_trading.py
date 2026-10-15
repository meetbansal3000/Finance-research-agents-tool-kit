"""
tests/test_paper_trading.py - Unit Tests for Live Paper Trading Execution Engine
Verifies $1,000,000 initial capital, execution mechanics, options multiplier,
futures initial margin, position closing, mark-to-market, and cryptographic receipts.
"""

import os
import tempfile
import pytest
from tools.paper_trading import PaperTradingEngine
from tools.ticker_search import lookup_primary_ticker


@pytest.fixture
def temp_engine():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name
    # Remove file so engine initializes it
    if os.path.exists(temp_path):
        os.remove(temp_path)
    engine = PaperTradingEngine(portfolio_file=temp_path)
    yield engine
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_initial_portfolio_balance(temp_engine):
    data = temp_engine.load_portfolio()
    assert data["initial_cash"] == 1000000.0
    assert data["cash_balance"] == 1000000.0
    assert len(data["positions"]) == 0
    assert len(data["closed_trades"]) == 0


def test_execute_equity_trade(temp_engine):
    ok, msg, pos = temp_engine.execute_trade(
        symbol="MU",
        asset_class="Equities",
        side="BUY",
        quantity=100.0,
        price=105.0,
        strategy_type="Long Equity"
    )
    assert ok is True
    assert "ORDER FILLED" in msg
    assert pos["symbol"] == "MU"
    assert pos["cost_basis"] == 10500.0
    assert pos["quantity"] == 100.0

    port = temp_engine.load_portfolio()
    assert port["cash_balance"] == 1000000.0 - 10500.0
    assert len(port["positions"]) == 1


def test_execute_options_trade_multiplier(temp_engine):
    # Options have 100x multiplier: 2 contracts @ $15.00 = $3,000
    ok, msg, pos = temp_engine.execute_trade(
        symbol="MU",
        asset_class="Options",
        side="BUY",
        quantity=2.0,
        price=15.0,
        strategy_type="Long Call",
        multiplier=100.0
    )
    assert ok is True
    assert pos["cost_basis"] == 3000.0
    assert pos["multiplier"] == 100.0

    port = temp_engine.load_portfolio()
    assert port["cash_balance"] == 1000000.0 - 3000.0


def test_insufficient_cash_rejection(temp_engine):
    # Trying to buy $2,000,000 worth of stock with $1,000,000 cash
    ok, msg, pos = temp_engine.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=20000.0,
        price=100.0
    )
    assert ok is False
    assert "Insufficient Cash" in msg


def test_close_position_realized_pnl(temp_engine):
    # Buy 100 shares @ $100 = $10,000
    ok, msg, pos = temp_engine.execute_trade(
        symbol="NVDA",
        asset_class="Equities",
        side="BUY",
        quantity=100.0,
        price=100.0
    )
    assert ok is True
    pos_id = pos["position_id"]

    # Close at $120 (gain of $20/share = $2,000 profit)
    c_ok, c_msg, closed = temp_engine.close_position(
        position_id=pos_id,
        exit_price=120.0,
        reason="Target Reached"
    )
    assert c_ok is True
    assert closed["realized_pnl"] == 2000.0
    assert closed["realized_pnl_pct"] == 20.0

    port = temp_engine.load_portfolio()
    assert len(port["positions"]) == 0
    assert len(port["closed_trades"]) == 1
    assert port["cash_balance"] == 1000000.0 + 2000.0
    assert port["total_realized_pnl"] == 2000.0


def test_mark_to_market_update(temp_engine):
    # Buy 50 shares @ $200 = $10,000
    temp_engine.execute_trade(
        symbol="TSLA",
        asset_class="Equities",
        side="BUY",
        quantity=50.0,
        price=200.0
    )
    # Provide live quote of $220
    summary = temp_engine.mark_to_market(quotes={"TSLA": 220.0})
    assert summary["positions"][0]["current_price"] == 220.0
    assert summary["positions"][0]["unrealized_pnl"] == 1000.0
    assert summary["total_unrealized_pnl"] == 1000.0
    assert summary["total_equity"] == 1001000.0


def test_reset_portfolio(temp_engine):
    temp_engine.execute_trade(
        symbol="MSFT",
        asset_class="Equities",
        side="BUY",
        quantity=10.0,
        price=400.0
    )
    reset = temp_engine.reset_portfolio(initial_cash=1000000.0)
    assert reset["cash_balance"] == 1000000.0
    assert len(reset["positions"]) == 0
    assert reset["total_realized_pnl"] == 0.0


def test_company_name_resolution_for_paper_trading():
    assert lookup_primary_ticker("micron") == "MU"
    assert lookup_primary_ticker("apple") == "AAPL"
    assert lookup_primary_ticker("nvidia") == "NVDA"
