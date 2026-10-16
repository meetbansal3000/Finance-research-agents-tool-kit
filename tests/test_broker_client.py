"""
tests/test_broker_client.py
Comprehensive unit tests for Multi-Exchange Router, Broker Connectivity & TCA Engine.
Verifies:
1. ExecutionCostModel across Equities, Options, Futures, and Crypto.
2. AlpacaBrokerClient simulation execution and account balance inspection.
3. InteractiveBrokersClient gateway bridge and SMART order routing.
4. MultiExchangeRouter venue routing, mode switching, and cryptographic provenance receipts.
5. End-to-end integration with PaperTradingEngine including TCA friction tracking.
"""

import os
import pytest
from tools.broker_client import (
    ExecutionCostModel,
    AlpacaBrokerClient,
    InteractiveBrokersClient,
    MultiExchangeRouter
)
from tools.paper_trading import PaperTradingEngine
import tempfile


@pytest.fixture
def temp_paper_engine():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name
    if os.path.exists(temp_path):
        os.remove(temp_path)
    engine = PaperTradingEngine(portfolio_file=temp_path)
    yield engine
    if os.path.exists(temp_path):
        os.remove(temp_path)


# =============================================================================
# 1. TRANSACTION COST ANALYSIS (TCA) TESTS
# =============================================================================

def test_equity_tca_execution_costs():
    costs = ExecutionCostModel.calculate_execution_costs(
        asset_class="Equities",
        side="BUY",
        quantity=500.0,
        price=100.0,
        daily_volatility_pct=2.0,
        average_daily_volume=500000.0,
        bid_ask_spread_pct=0.04
    )
    assert costs["asset_class"] == "Equities"
    assert costs["side"] == "BUY"
    assert costs["quantity"] == 500.0
    assert costs["benchmark_price"] == 100.0
    assert costs["notional_usd"] == 50000.0
    assert costs["half_spread_cost_usd"] > 0.0
    assert costs["market_impact_slippage_usd"] > 0.0
    assert costs["effective_price"] > 100.0  # Buy side pays spread + impact
    assert costs["total_friction_usd"] > 0.0
    assert costs["friction_basis_points"] > 0.0


def test_options_tca_contract_fees():
    costs = ExecutionCostModel.calculate_execution_costs(
        asset_class="Options",
        side="BUY",
        quantity=10.0,
        price=5.50
    )
    assert costs["asset_class"] == "Options"
    # Options fees: ($0.65 + $0.02 + $0.05) * 10 contracts = $7.20
    assert costs["commission_and_clearing_fees_usd"] == 7.20
    assert costs["effective_price"] > 5.50
    assert costs["total_friction_usd"] > 7.20


def test_futures_tca_exchange_fees():
    costs = ExecutionCostModel.calculate_execution_costs(
        asset_class="Futures",
        side="SELL",
        quantity=2.0,
        price=5000.0
    )
    assert costs["asset_class"] == "Futures"
    # Futures fees: ($1.40 + $0.02 + $0.85) * 2 = $4.54
    assert costs["commission_and_clearing_fees_usd"] == 4.54
    assert costs["effective_price"] < 5000.0  # Sell side receives less after spread + impact


def test_crypto_tca_maker_vs_taker():
    taker_costs = ExecutionCostModel.calculate_execution_costs(
        asset_class="Crypto",
        side="BUY",
        quantity=1.0,
        price=60000.0,
        is_maker=False
    )
    maker_costs = ExecutionCostModel.calculate_execution_costs(
        asset_class="Crypto",
        side="BUY",
        quantity=1.0,
        price=60000.0,
        is_maker=True
    )
    # Taker fee (0.25%) is higher than Maker fee (0.15%)
    assert taker_costs["commission_and_clearing_fees_usd"] > maker_costs["commission_and_clearing_fees_usd"]


# =============================================================================
# 2. ALPACA BROKER CLIENT TESTS
# =============================================================================

def test_alpaca_simulation_mode_account():
    client = AlpacaBrokerClient(is_paper=True)
    assert client.is_configured is False
    acct = client.get_account()
    assert acct["status"] == "SIMULATED_ACTIVE"
    assert acct["equity_usd"] == 1000000.0
    assert acct["cash_usd"] == 1000000.0
    assert acct["buying_power_usd"] == 2000000.0


def test_alpaca_simulation_order_execution():
    client = AlpacaBrokerClient(is_paper=True)
    ok, msg, res = client.submit_order(
        symbol="AAPL",
        quantity=50.0,
        side="buy",
        order_type="market",
        price=220.0
    )
    assert ok is True
    assert "Sim Fill" in msg
    assert res["symbol"] == "AAPL"
    assert res["status"] == "FILLED"
    assert "provenance_ledger_id" in res
    assert res["filled_avg_price"] > 0.0


# =============================================================================
# 3. INTERACTIVE BROKERS CLIENT TESTS
# =============================================================================

def test_ibkr_standby_account():
    client = InteractiveBrokersClient()
    acct = client.get_account()
    assert acct["status"] == "GATEWAY_STANDBY"
    assert acct["equity_usd"] == 1000000.0
    assert acct["buying_power_usd"] == 4000000.0


def test_ibkr_submit_order_smart_route():
    client = InteractiveBrokersClient()
    ok, msg, res = client.submit_order(
        symbol="NVDA",
        quantity=25.0,
        side="buy",
        order_type="market",
        price=125.0
    )
    assert ok is True
    assert "IBKR SMART Fill" in msg
    assert res["symbol"] == "NVDA"
    assert res["status"] == "FILLED"
    assert "provenance_ledger_id" in res


# =============================================================================
# 4. MULTI-EXCHANGE ROUTER TESTS
# =============================================================================

def test_multi_exchange_router_modes():
    router = MultiExchangeRouter(active_mode="SIMULATION_PAPER")
    assert router.active_mode == "SIMULATION_PAPER"
    assert router.AVAILABLE_MODES == ["SIMULATION_PAPER", "ALPACA_PAPER"]

    # Allowed paper modes
    assert router.set_execution_mode("ALPACA_PAPER") is True
    assert router.active_mode == "ALPACA_PAPER"
    assert router.alpaca_client.is_paper is True

    # Prohibited live modes MUST be refused
    assert router.set_execution_mode("ALPACA_LIVE") is False
    assert router.active_mode == "ALPACA_PAPER"

    assert router.set_execution_mode("IBKR_GATEWAY") is False
    assert router.active_mode == "ALPACA_PAPER"

    assert router.set_execution_mode("SIMULATION_PAPER") is True
    assert router.active_mode == "SIMULATION_PAPER"

    # Arbitrary invalid mode returns False
    assert router.set_execution_mode("INVALID_EXCHANGE") is False


def test_refuse_live_trading_urls(monkeypatch):
    """
    Strict guardrail verification: any attempt to use a live URL
    or initialize a live broker client must be refused.
    """
    # 1. Reject is_paper=False
    with pytest.raises(ValueError, match="Live trading is strictly prohibited"):
        AlpacaBrokerClient(is_paper=False)

    # 2. Reject explicit live Alpaca URL
    with pytest.raises(ValueError, match="Live trading URL"):
        AlpacaBrokerClient(base_url="https://api.alpaca.markets")

    with pytest.raises(ValueError, match="Live trading URL"):
        AlpacaBrokerClient(base_url="https://api.alpaca.markets/v2")

    # 3. Reject live URL via environment variable override
    monkeypatch.setenv("APCA_API_BASE_URL", "https://api.alpaca.markets")
    with pytest.raises(ValueError, match="Live trading URL"):
        AlpacaBrokerClient()

    # 4. Reject live URL pattern (e.g. production/live endpoint)
    with pytest.raises(ValueError, match="Live trading URL"):
        AlpacaBrokerClient(base_url="https://live-trading.brokerage.com/v1")

    # 5. Reject setter modification to a live URL
    client = AlpacaBrokerClient(is_paper=True, base_url="https://paper-api.alpaca.markets")
    with pytest.raises(ValueError, match="Live trading URL"):
        client.base_url = "https://api.alpaca.markets"

    # 6. Valid paper URLs succeed
    valid_client = AlpacaBrokerClient(is_paper=True, base_url="https://paper-api.alpaca.markets")
    assert valid_client.base_url == "https://paper-api.alpaca.markets"
    assert valid_client.is_paper is True


def test_multi_exchange_router_execution():
    router = MultiExchangeRouter(active_mode="SIMULATION_PAPER")
    ok, msg, rec = router.route_and_execute(
        symbol="TSLA",
        asset_class="Equities",
        side="BUY",
        quantity=10.0,
        price=210.0,
        preferred_venue="IEX (Speed Bump)"
    )
    assert ok is True
    assert "IEX (Speed Bump)" in msg
    assert rec["symbol"] == "TSLA"
    assert rec["routed_venue"] == "IEX (Speed Bump)"
    assert rec["status"] == "FILLED"
    assert "tca" in rec
    assert "provenance_ledger_id" in rec


# =============================================================================
# 5. PAPER TRADING ENGINE WITH BROKER ROUTING INTEGRATION
# =============================================================================

def test_paper_trading_with_venue_routing(temp_paper_engine):
    ok, msg, pos = temp_paper_engine.execute_trade(
        symbol="AMD",
        asset_class="Equities",
        side="BUY",
        quantity=40.0,
        price=150.0,
        strategy_type="Momentum Long",
        routing_venue="NASDAQ",
        execution_mode="SIMULATION_PAPER"
    )
    assert ok is True
    assert "via NASDAQ" in msg
    assert pos["routing_venue"] == "NASDAQ"
    assert pos["execution_mode"] == "SIMULATION_PAPER"
    assert "tca" in pos
    assert pos["effective_entry_price"] >= 150.0
    assert pos["cost_basis"] == 40.0 * 150.0  # Nominal base preserved
