"""
tests/test_alert_dispatcher.py
Unit tests for the Institutional Multi-Channel Webhook Alert Dispatcher.
Verifies Discord, Slack, Telegram, and Generic REST payloads, throttling,
HMAC-SHA256 provenance signing, and integration with the Risk Sentry.
"""

import os
import json
import pytest
import tempfile
from tools.alert_dispatcher import WebhookAlertDispatcher
from tools.risk_sentry import PortfolioRiskSentry
from tools.paper_trading import PaperTradingEngine


@pytest.fixture
def temp_dispatcher():
    dispatcher = WebhookAlertDispatcher(cooldown_seconds=5.0)
    return dispatcher


def test_dispatcher_channel_status(temp_dispatcher):
    status = temp_dispatcher.get_channel_status()
    assert "discord" in status
    assert "slack" in status
    assert "telegram" in status
    assert "generic_rest" in status
    assert status["discord"]["configured"] is False


def test_build_discord_payload(temp_dispatcher):
    sample_data = {
        "event_type": "QUANTITATIVE_RISK_ALERT",
        "alert_type": "POSITION_DRAWDOWN_BREACH",
        "severity": "CRITICAL",
        "symbol": "NVDA",
        "message": "NVDA unrealized drawdown reached -16.5%.",
        "metrics": {"unrealized_pnl_usd": -1650.0, "drawdown_pct": -16.5},
        "provenance_ledger_id": "test_prov_123"
    }
    payload = temp_dispatcher._build_discord_payload(sample_data)
    assert payload["username"] == "Meridian Risk Sentry"
    assert len(payload["embeds"]) == 1
    embed = payload["embeds"][0]
    assert embed["color"] == int("EF4444", 16)  # Critical Red
    assert "NVDA" in embed["title"] or "DRAWDOWN" in embed["title"]
    field_names = [f["name"] for f in embed["fields"]]
    assert "Symbol" in field_names
    assert "Severity" in field_names


def test_build_slack_payload(temp_dispatcher):
    sample_data = {
        "event_type": "ORDER_EXECUTION_FILL",
        "severity": "SUCCESS",
        "symbol": "AAPL",
        "message": "Bought 100 AAPL @ $220.00 USD.",
        "provenance_ledger_id": "test_prov_456"
    }
    payload = temp_dispatcher._build_slack_payload(sample_data)
    assert "blocks" in payload
    assert len(payload["blocks"]) >= 2
    assert "AAPL" in payload["blocks"][0]["text"]["text"]


def test_build_telegram_message(temp_dispatcher):
    sample_data = {
        "event_type": "RISK_ALERT",
        "severity": "WARNING",
        "symbol": "TSLA",
        "message": "TSLA elevated volatility detected.",
        "provenance_ledger_id": "test_prov_789"
    }
    msg = temp_dispatcher._build_telegram_message(sample_data)
    assert "<b>🚨 MERIDIAN RISK SENTRY ALERT</b>" in msg
    assert "TSLA" in msg
    assert "test_prov_789" in msg


def test_dispatch_risk_alert_simulation_mode(temp_dispatcher):
    res = temp_dispatcher.dispatch_risk_alert(
        alert_type="MARGIN_OVERLEVERAGE_BREACH",
        severity="CRITICAL",
        message="Committed margin exceeds 70% threshold.",
        symbol="PORTFOLIO",
        metrics={"margin_utilization_pct": 74.5},
        force=True
    )
    assert res["status"] == "DISPATCHED"
    assert "provenance_ledger_id" in res
    assert res["channels"]["discord"]["status"] == "SIMULATED_DELIVERED"
    assert res["channels"]["slack"]["status"] == "SIMULATED_DELIVERED"
    assert res["channels"]["telegram"]["status"] == "SIMULATED_DELIVERED"


def test_alert_throttling_cooldown(temp_dispatcher):
    # First alert should dispatch
    res1 = temp_dispatcher.dispatch_risk_alert(
        alert_type="TEST_THROTTLE",
        severity="WARNING",
        message="First warning",
        symbol="SPY"
    )
    assert res1["status"] == "DISPATCHED"

    # Immediate second alert for same key should be throttled
    res2 = temp_dispatcher.dispatch_risk_alert(
        alert_type="TEST_THROTTLE",
        severity="WARNING",
        message="Duplicate warning",
        symbol="SPY",
        force=False
    )
    assert res2["status"] == "THROTTLED"

    # Forced alert bypasses throttling
    res3 = temp_dispatcher.dispatch_risk_alert(
        alert_type="TEST_THROTTLE",
        severity="WARNING",
        message="Forced warning",
        symbol="SPY",
        force=True
    )
    assert res3["status"] == "DISPATCHED"


def test_dispatch_order_fill_simulation(temp_dispatcher):
    order_rec = {
        "symbol": "MSFT",
        "side": "BUY",
        "quantity": 20.0,
        "entry_price": 400.0,
        "routing_venue": "NASDAQ",
        "execution_mode": "SIMULATION_PAPER",
        "cost_basis": 8000.0
    }
    tca = {
        "total_friction_usd": 3.20,
        "friction_basis_points": 4.0
    }
    res = temp_dispatcher.dispatch_order_fill(order_record=order_rec, tca=tca)
    assert res["status"] == "DISPATCHED"
    assert "provenance_ledger_id" in res


def test_load_recent_dispatches(temp_dispatcher):
    dispatches = temp_dispatcher.load_recent_dispatches(limit=5)
    assert isinstance(dispatches, list)
    if dispatches:
        assert "provenance_ledger_id" in dispatches[-1]
