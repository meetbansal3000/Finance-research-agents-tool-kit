"""
tests/test_fill_model.py - Comprehensive Unit Tests & Worked Examples for Institutional Fill Model.

Covers:
1. Market order modelled spread, slippage, and fee calculations with exact step-by-step arithmetic.
2. Limit orders that fill when crossed vs stay unfilled when price does not cross.
3. Order rejection when quote timestamp exceeds configurable maximum age (stale quotes).
4. Partial fills when order size exceeds configured volume participation limit (% of ADV).
5. Market hours validation (blocking outside regular 09:30-16:00 ET Mon-Fri, permitting 24/7 crypto).
6. Corporate actions: Cash dividends (credited to long, debited from short).
7. Corporate actions: Stock splits (multiplying shares, dividing price, preserving total cost basis).
8. Carrying costs: Short borrow fee calculation and cash deduction.
"""

import os
import math
import tempfile
import datetime
import zoneinfo
import pytest

from tools.fill_model import RealisticFillModel
from tools.paper_trading import PaperTradingEngine
from tools.broker_client import ExecutionCostModel, MultiExchangeRouter


ET_TZ = zoneinfo.ZoneInfo("America/New_York")


@pytest.fixture
def temp_engine():
    """Temporary isolated paper trading engine."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name
    if os.path.exists(temp_path):
        os.remove(temp_path)
    engine = PaperTradingEngine(portfolio_file=temp_path, enforce_journal_gate=False)
    yield engine
    if os.path.exists(temp_path):
        os.remove(temp_path)


# =============================================================================
# 1. MARKET ORDER SPREAD, SLIPPAGE & FEES WORKED EXAMPLE
# =============================================================================

def test_market_order_modelled_slippage_and_fees():
    """
    Worked Example:
    Asset: 1,000 shares of NVDA @ $100.00 benchmark price.
    ADV = 1,000,000 shares.
    Bid-Ask Spread = 4 bps (0.04%).
    Daily Volatility = 1.80%.

    Step-by-Step Arithmetic:
    1. Notional: 1,000 * 100.00 = $100,000.00
    2. Half-Spread: (0.04% / 2) = 0.02% = 0.0002
       Spread Cost = $100,000.00 * 0.0002 = $20.00 ($0.02 / share)
    3. Square-Root Market Impact (Almgren-Chriss):
       Participation Rate = 1,000 / 1,000,000 = 0.001
       Gamma = 0.35, Sigma = 0.018
       Impact % = 0.35 * 0.018 * sqrt(0.001) * 100%
                = 0.35 * 0.018 * 0.0316227766 * 100%
                = 0.0199223%
       Slippage per share = $100.00 * (0.0199223 / 100) = $0.0199223
       Slippage Cost = 1,000 * $0.0199223 = $19.92
    4. Buy Effective Price:
       P_eff = $100.00 + $0.02 (spread) + $0.019922 (slippage) = $100.0399
    5. Sell Regulatory Fees:
       SEC Fee = $100,000 * 0.0000278 = $2.78
       FINRA Fee = 1,000 * 0.000166 = $0.166 -> $0.17
       Total Sell Commission & Clearing = $2.95
    """
    # 1. Test BUY order
    buy_tca = ExecutionCostModel.calculate_execution_costs(
        asset_class="Equities",
        side="BUY",
        quantity=1000.0,
        price=100.0,
        daily_volatility_pct=1.80,
        average_daily_volume=1000000.0,
        bid_ask_spread_pct=0.04
    )

    assert buy_tca["notional_usd"] == 100000.0
    assert buy_tca["half_spread_cost_usd"] == 20.00
    assert math.isclose(buy_tca["market_impact_slippage_usd"], 19.92, abs_tol=0.05)
    assert buy_tca["commission_and_clearing_fees_usd"] == 0.0  # Zero retail commission on buy
    assert math.isclose(buy_tca["effective_price"], 100.0399, abs_tol=0.001)

    # 2. Test SELL order
    sell_tca = ExecutionCostModel.calculate_execution_costs(
        asset_class="Equities",
        side="SELL",
        quantity=1000.0,
        price=100.0,
        daily_volatility_pct=1.80,
        average_daily_volume=1000000.0,
        bid_ask_spread_pct=0.04
    )
    # Regulatory SEC (2.78) + FINRA (0.17) = $2.95
    assert math.isclose(sell_tca["commission_and_clearing_fees_usd"], 2.95, abs_tol=0.02)
    # Sell effective price is below benchmark (market price minus half spread minus slippage)
    assert sell_tca["effective_price"] < 100.0
    assert math.isclose(sell_tca["effective_price"], 100.0 - 0.02 - 0.019922, abs_tol=0.001)


# =============================================================================
# 2. LIMIT ORDER CROSSING VS UNFILLED WORKED EXAMPLE
# =============================================================================

def test_limit_order_crossing_vs_unfilled(temp_engine):
    """
    Worked Example:
    Case A (Unfilled): BUY limit order @ $95.00 when market price is $100.00.
           Market did not cross downwards (100.00 > 95.00). Must NOT fill.
    Case B (Filled): BUY limit order @ $105.00 when market price is $100.00.
           Market is below limit (100.00 <= 105.00). Must fill.
    Case C (Unfilled): SELL limit order @ $110.00 when market price is $100.00.
           Market did not reach upward limit (100.00 < 110.00). Must NOT fill.
    Case D (Filled): SELL limit order @ $98.00 when market price is $100.00.
           Market is above limit (100.00 >= 98.00). Must fill.
    """
    # Case A: BUY limit @ $95.00, market @ $100.00 -> Unfilled
    ok_a, msg_a, res_a = temp_engine.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=100.0,
        price=100.0,
        order_type="limit",
        limit_price=95.0
    )
    assert ok_a is False
    assert res_a["status"] == "UNFILLED"
    assert res_a["reason"] == "PRICE_DID_NOT_CROSS"
    assert "did not cross" in msg_a.lower() or "not crossed" in msg_a.lower()

    # Case B: BUY limit @ $105.00, market @ $100.00 -> Filled
    ok_b, msg_b, res_b = temp_engine.execute_trade(
        symbol="AAPL",
        asset_class="Equities",
        side="BUY",
        quantity=100.0,
        price=100.0,
        order_type="limit",
        limit_price=105.0
    )
    assert ok_b is True
    assert res_b["order_type"] == "LIMIT"
    assert res_b["effective_entry_price"] <= 105.0  # Does not violate limit

    # Case C: SELL limit @ $110.00, market @ $100.00 -> Unfilled
    ok_c, msg_c, res_c = temp_engine.execute_trade(
        symbol="MSFT",
        asset_class="Equities",
        side="SELL",
        quantity=50.0,
        price=100.0,
        order_type="limit",
        limit_price=110.0
    )
    assert ok_c is False
    assert res_c["status"] == "UNFILLED"
    assert res_c["reason"] == "PRICE_DID_NOT_CROSS"

    # Case D: SELL limit @ $98.00, market @ $100.00 -> Filled
    ok_d, msg_d, res_d = temp_engine.execute_trade(
        symbol="MSFT",
        asset_class="Equities",
        side="SELL",
        quantity=50.0,
        price=100.0,
        order_type="limit",
        limit_price=98.0
    )
    assert ok_d is True
    assert res_d["order_type"] == "LIMIT"


# =============================================================================
# 3. STALE QUOTE REJECTION WORKED EXAMPLE
# =============================================================================

def test_stale_quote_rejection(temp_engine):
    """
    Worked Example:
    Reference Time: 2026-10-16 12:00:00 UTC.
    Max Allowed Age: 900 seconds (15 minutes).
    Stale Quote: 2026-10-16 11:40:00 UTC (1,200 seconds old -> > 900s). Rejection required.
    Fresh Quote: 2026-10-16 11:59:00 UTC (60 seconds old -> <= 900s). Execution permitted.
    """
    current_time = datetime.datetime(2026, 10, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)
    stale_timestamp = datetime.datetime(2026, 10, 16, 11, 40, 0, tzinfo=datetime.timezone.utc)
    fresh_timestamp = datetime.datetime(2026, 10, 16, 11, 59, 0, tzinfo=datetime.timezone.utc)

    # 1. Attempt order with stale quote -> Rejected
    ok_stale, msg_stale, res_stale = temp_engine.execute_trade(
        symbol="GOOGL",
        asset_class="Equities",
        side="BUY",
        quantity=50.0,
        price=180.0,
        quote_timestamp=stale_timestamp,
        max_quote_age_seconds=900.0,
        current_time=current_time
    )
    assert ok_stale is False
    assert res_stale["status"] == "REJECTED_STALE_QUOTE"
    assert res_stale["quote_age_seconds"] == 1200.0
    assert "Quote Stale" in msg_stale

    # 2. Attempt order with fresh quote -> Accepted
    ok_fresh, msg_fresh, res_fresh = temp_engine.execute_trade(
        symbol="GOOGL",
        asset_class="Equities",
        side="BUY",
        quantity=50.0,
        price=180.0,
        quote_timestamp=fresh_timestamp,
        max_quote_age_seconds=900.0,
        current_time=current_time
    )
    assert ok_fresh is True
    assert "ORDER FILLED" in msg_fresh


# =============================================================================
# 4. PARTIAL FILL ON ADV VOLUME THRESHOLD WORKED EXAMPLE
# =============================================================================

def test_partial_fill_on_adv_share_threshold(temp_engine):
    """
    Worked Example:
    Order Quantity = 50,000 shares.
    Average Daily Volume (ADV) = 200,000 shares.
    Max Volume Share = 10% (0.10).
    Max Executable Fill = 200,000 * 0.10 = 20,000 shares.
    Expected Result:
    - Filled Quantity: 20,000 shares.
    - Unfilled Quantity: 30,000 shares.
    - Status: PARTIALLY_FILLED.
    - Portfolio position reflects 20,000 shares.
    """
    temp_engine.reset_portfolio(initial_cash=1000000.0)
    ok, msg, pos = temp_engine.execute_trade(
        symbol="INTC",
        asset_class="Equities",
        side="BUY",
        quantity=50000.0,
        price=25.0,
        average_daily_volume=200000.0,
        max_volume_share=0.10
    )

    assert ok is True
    assert pos["is_partial"] is True
    assert pos["quantity"] == 20000.0
    assert pos["requested_quantity"] == 50000.0
    assert pos["unfilled_quantity"] == 30000.0
    assert "PARTIALLY FILLED" in msg
    assert "30,000.00 remaining unfilled" in msg

    # Verify portfolio state
    data = temp_engine.load_portfolio()
    assert len(data["positions"]) == 1
    assert data["positions"][0]["quantity"] == 20000.0


# =============================================================================
# 5. MARKET HOURS VALIDATION WORKED EXAMPLE
# =============================================================================

def test_market_hours_validation(temp_engine):
    """
    Worked Example:
    - Wednesday 2026-10-14 21:00 ET (Night, outside 09:30 - 16:00 ET): Equities REJECTED.
    - Saturday 2026-10-17 14:00 ET (Weekend): Equities REJECTED.
    - Wednesday 2026-10-14 11:30 ET (Regular hours): Equities ACCEPTED.
    - Saturday 2026-10-17 14:00 ET (Weekend): Crypto ACCEPTED (24/7 market).
    """
    wed_closed = datetime.datetime(2026, 10, 14, 21, 0, 0, tzinfo=ET_TZ)
    sat_weekend = datetime.datetime(2026, 10, 17, 14, 0, 0, tzinfo=ET_TZ)
    wed_open = datetime.datetime(2026, 10, 14, 11, 30, 0, tzinfo=ET_TZ)

    # 1. Equities outside hours -> Rejected
    ok_closed, msg_closed, res_closed = temp_engine.execute_trade(
        symbol="SPY",
        asset_class="Equities",
        side="BUY",
        quantity=10.0,
        price=500.0,
        enforce_market_hours=True,
        current_time=wed_closed
    )
    assert ok_closed is False
    assert res_closed["status"] == "REJECTED_MARKET_CLOSED"
    assert "outside regular market hours" in msg_closed

    # 2. Equities weekend -> Rejected
    ok_sat, msg_sat, res_sat = temp_engine.execute_trade(
        symbol="SPY",
        asset_class="Equities",
        side="BUY",
        quantity=10.0,
        price=500.0,
        enforce_market_hours=True,
        current_time=sat_weekend
    )
    assert ok_sat is False
    assert res_sat["status"] == "REJECTED_MARKET_CLOSED"
    assert "Weekend trading is disabled" in msg_sat

    # 3. Equities regular session -> Accepted
    ok_open, msg_open, res_open = temp_engine.execute_trade(
        symbol="SPY",
        asset_class="Equities",
        side="BUY",
        quantity=10.0,
        price=500.0,
        enforce_market_hours=True,
        current_time=wed_open
    )
    assert ok_open is True

    # 4. Crypto weekend -> Accepted (24/7)
    ok_crypto, msg_crypto, res_crypto = temp_engine.execute_trade(
        symbol="BTC",
        asset_class="Crypto",
        side="BUY",
        quantity=0.5,
        price=65000.0,
        enforce_market_hours=True,
        current_time=sat_weekend
    )
    assert ok_crypto is True


# =============================================================================
# 6. CORPORATE ACTIONS: CASH DIVIDENDS WORKED EXAMPLE
# =============================================================================

def test_corporate_actions_dividends(temp_engine):
    """
    Worked Example:
    Open Long: 500 AAPL shares.
    Open Short: 200 TSLA shares.
    Initial Cash = $1,000,000.
    1. AAPL declares $0.25 dividend:
       Long receives: 500 * $0.25 = +$125.00 cash credit.
    2. TSLA declares $0.50 dividend:
       Short seller pays: 200 * $0.50 = -$100.00 cash debit.
    Net Cash Impact = +$25.00.
    """
    temp_engine.reset_portfolio(initial_cash=1000000.0)

    # Buy 500 AAPL @ $100.00 ($50,000 cost)
    temp_engine.execute_trade(symbol="AAPL", asset_class="Equities", side="BUY", quantity=500.0, price=100.0)
    # Short 200 TSLA @ $200.00 ($40,000 margin buffer)
    temp_engine.execute_trade(symbol="TSLA", asset_class="Equities", side="SELL", quantity=200.0, price=200.0)

    cash_pre_div = temp_engine.load_portfolio()["cash_balance"]

    # 1. Apply AAPL dividend
    res_aapl = temp_engine.apply_dividend(symbol="AAPL", dividend_per_share=0.25)
    assert res_aapl["success"] is True
    assert res_aapl["total_credited_usd"] == 125.0
    assert res_aapl["total_debited_usd"] == 0.0

    # 2. Apply TSLA dividend
    res_tsla = temp_engine.apply_dividend(symbol="TSLA", dividend_per_share=0.50)
    assert res_tsla["success"] is True
    assert res_tsla["total_debited_usd"] == 100.0

    cash_post_div = temp_engine.load_portfolio()["cash_balance"]
    assert math.isclose(cash_post_div - cash_pre_div, 25.0, abs_tol=0.01)


# =============================================================================
# 7. CORPORATE ACTIONS: STOCK SPLITS WORKED EXAMPLE
# =============================================================================

def test_corporate_actions_stock_splits(temp_engine):
    """
    Worked Example:
    Long Position: 100 NVDA shares @ $120.00 entry price.
    Total Cost Basis: $12,000.00.
    Corporate Action: 4-for-1 forward stock split (ratio = 4.0).
    Expected Result:
    - Position Quantity becomes 100 * 4 = 400 shares.
    - Entry Price becomes $120.00 / 4 = $30.00.
    - Total Cost Basis remains $12,000.00.
    """
    temp_engine.reset_portfolio(initial_cash=1000000.0)
    temp_engine.execute_trade(symbol="NVDA", asset_class="Equities", side="BUY", quantity=100.0, price=120.0)

    split_res = temp_engine.apply_stock_split(symbol="NVDA", ratio=4.0)
    assert split_res["success"] is True
    assert len(split_res["adjusted_positions"]) == 1

    adj = split_res["adjusted_positions"][0]
    assert adj["old_quantity"] == 100.0
    assert adj["new_quantity"] == 400.0
    assert adj["old_entry_price"] == 120.0
    assert adj["new_entry_price"] == 30.0

    port = temp_engine.load_portfolio()
    pos = port["positions"][0]
    assert pos["quantity"] == 400.0
    assert pos["entry_price"] == 30.0
    assert pos["cost_basis"] == 12000.0  # Cost basis strictly preserved


# =============================================================================
# 8. SHORT BORROW COST WORKED EXAMPLE
# =============================================================================

def test_short_borrow_cost_accrual(temp_engine):
    """
    Worked Example:
    Short Position: 100 TSLA shares @ $250.00.
    Notional Value = 100 * 250.00 = $25,000.00.
    Annual Borrow Fee Rate = 3.6% (0.036).
    Days Accrued = 10 days.

    Calculation:
    Daily Rate = 0.036 / 360 = 0.0001 (1 bp/day).
    10-day Borrow Cost = $25,000.00 * 0.0001 * 10 = $25.00.
    Expected:
    - Cash balance debited by $25.00.
    - Position accumulated_borrow_fees equals $25.00.
    """
    temp_engine.reset_portfolio(initial_cash=1000000.0)
    temp_engine.execute_trade(symbol="TEST_SHORT", asset_class="Equities", side="SELL", quantity=100.0, price=250.0)

    cash_pre = temp_engine.load_portfolio()["cash_balance"]

    borrow_res = temp_engine.apply_short_borrow_cost(days=10, annual_borrow_rate=0.036)
    assert borrow_res["success"] is True
    assert borrow_res["total_borrow_cost_usd"] == 25.00

    cash_post = temp_engine.load_portfolio()["cash_balance"]
    assert math.isclose(cash_pre - cash_post, 25.00, abs_tol=0.01)

    port = temp_engine.load_portfolio()
    assert port["positions"][0]["accumulated_borrow_fees"] == 25.00


# =============================================================================
# 9. MULTI-EXCHANGE ROUTER INTEGRATION WITH FILL MODEL
# =============================================================================

def test_multi_exchange_router_fill_model_integration():
    """Verify that MultiExchangeRouter routes orders through RealisticFillModel seamlessly."""
    router = MultiExchangeRouter(active_mode="SIMULATION_PAPER")

    # 1. Limit order uncrossed rejection
    ok_limit, msg_limit, res_limit = router.route_and_execute(
        symbol="AMD",
        asset_class="Equities",
        side="BUY",
        quantity=50.0,
        price=150.0,
        order_type="limit",
        limit_price=140.0  # Limit is below market price
    )
    assert ok_limit is False
    assert res_limit["status"] == "UNFILLED"

    # 2. Market order with partial fill on ADV share
    ok_part, msg_part, res_part = router.route_and_execute(
        symbol="AMD",
        asset_class="Equities",
        side="BUY",
        quantity=40000.0,
        price=150.0,
        average_daily_volume=100000.0,
        max_volume_share=0.10
    )
    assert ok_part is True
    assert res_part["is_partial"] is True
    assert res_part["quantity"] == 10000.0  # 10% of 100,000
    assert res_part["unfilled_quantity"] == 30000.0
