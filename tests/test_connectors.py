"""
tests/test_connectors.py
Comprehensive test suite for Meridian External AI Connectors:
1. Model Context Protocol (MCP) Server (JSON-RPC 2.0 over stdio)
2. Groq & OpenAI Universal Function Calling Tool Engine
"""

import os
import json
import pytest
from typing import Dict, Any

from connectors.mcp_server import (
    MCP_TOOLS,
    dispatch_tool,
    process_message
)
from connectors.groq_connector import (
    FINANCIAL_TOOLS_SCHEMA,
    execute_tool_call,
    run_groq_agent
)
from tools.paper_trading import PaperTradingEngine, INITIAL_PORTFOLIO_CASH


EXPECTED_TOOL_NAMES = [
    "resolve_ticker",
    "get_live_quote",
    "get_options_chain",
    "calculate_options_greeks",
    "analyze_options_strategy",
    "simulate_econometric_probability",
    "execute_paper_trade",
    "get_paper_portfolio",
    "close_paper_position",
    "run_multi_asset_committee"
]


def test_mcp_tools_list_specifications():
    """Verify that all 10 institutional tools are correctly registered with valid MCP schemas."""
    assert len(MCP_TOOLS) == 10
    names = [t["name"] for t in MCP_TOOLS]
    for expected in EXPECTED_TOOL_NAMES:
        assert expected in names

    for t in MCP_TOOLS:
        assert "name" in t
        assert "description" in t and len(t["description"]) > 20
        assert "inputSchema" in t
        schema = t["inputSchema"]
        assert schema.get("type") == "object"
        assert "properties" in schema


def test_openai_groq_schema_specifications():
    """Verify that FINANCIAL_TOOLS_SCHEMA conforms to OpenAI & Groq tool calling specification."""
    assert len(FINANCIAL_TOOLS_SCHEMA) == 10
    for tool_entry in FINANCIAL_TOOLS_SCHEMA:
        assert tool_entry["type"] == "function"
        fn = tool_entry["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert fn["parameters"].get("type") == "object"


def test_mcp_protocol_handshake_lifecycle():
    """Test full JSON-RPC 2.0 MCP message processing cycle."""
    # 1. Initialize
    init_res = process_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init_res["id"] == 1
    assert "result" in init_res
    assert init_res["result"]["serverInfo"]["name"] == "meridian-finance-workstation"

    # 2. Notifications initialized
    notify_res = process_message({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert notify_res is None

    # 3. Ping
    ping_res = process_message({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert ping_res["id"] == 2
    assert ping_res["result"] == {}

    # 4. Tools list
    list_res = process_message({"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}})
    assert list_res["id"] == 3
    assert len(list_res["result"]["tools"]) == 10

    # 5. Method not found error
    err_res = process_message({"jsonrpc": "2.0", "id": 4, "method": "unsupported_method"})
    assert err_res["id"] == 4
    assert "error" in err_res
    assert err_res["error"]["code"] == -32601


def test_dispatch_resolve_ticker():
    """Test resolve_ticker tool dispatch with informal company name."""
    res = dispatch_tool("resolve_ticker", {"query": "micron"})
    assert isinstance(res, dict)
    assert res.get("symbol") == "MU"
    assert "Micron" in res.get("name", "")
    assert res.get("price", 0.0) > 0.0
    assert res.get("atm_strike", 0.0) > 0.0
    assert res.get("atm_iv_pct", 0.0) > 0.0
    assert res.get("resolved") is True


def test_dispatch_get_live_quote():
    """Test get_live_quote tool dispatch for standard equity."""
    res = dispatch_tool("get_live_quote", {"symbol": "AAPL"})
    assert isinstance(res, dict)
    assert res.get("symbol") == "AAPL"
    assert res.get("last_price", 0.0) > 0.0
    assert "currency" in res


def test_dispatch_calculate_options_greeks():
    """Test calculate_options_greeks tool dispatch with Black-Scholes engine."""
    res = dispatch_tool("calculate_options_greeks", {
        "spot": 100.0,
        "strike": 100.0,
        "dte": 30,
        "iv": 0.25,
        "r": 0.045,
        "option_type": "call"
    })
    assert isinstance(res, dict)
    assert res["fair_value"] > 0.0
    # At-the-money call option delta should be near 0.50
    assert 0.45 <= res["delta"] <= 0.65
    assert res["gamma"] > 0.0
    assert res["vega_per_1pct"] > 0.0


def test_dispatch_simulate_econometric_probability():
    """Test simulate_econometric_probability tool across modes."""
    # 1. PDF/CDF
    res_cone = dispatch_tool("simulate_econometric_probability", {
        "mode": "pdf_cdf",
        "spot": 100.0,
        "dte": 30,
        "volatility": 0.25
    })
    assert res_cone["mode"] == "pdf_cdf"
    assert "expected_ranges" in res_cone
    ranges = res_cone["expected_ranges"]
    assert ranges["minus_1_sigma"] < ranges["median_expected"] < ranges["plus_1_sigma"]

    # 2. Single Stock Hitting Time
    res_single = dispatch_tool("simulate_econometric_probability", {
        "mode": "single_stock",
        "spot": 100.0,
        "target_price": 110.0,
        "dte": 45,
        "volatility": 0.30
    })
    assert "prob_touch_target_pct" in res_single
    assert "prob_close_above_target_pct" in res_single
    assert 0.0 <= res_single["prob_touch_target_pct"] <= 100.0

    # 3. Cornish-Fisher VaR
    res_cf = dispatch_tool("simulate_econometric_probability", {
        "mode": "cornish_fisher",
        "spot": 100.0,
        "dte": 30,
        "volatility": 0.25
    })
    assert "cornish_fisher_z_95" in res_cf
    assert "parametric_var_95_pct" in res_cf


def test_dispatch_paper_trading_lifecycle(tmp_path):
    """Test full execute, query, and close cycle in paper trading via connector dispatch."""
    test_portfolio_file = os.path.join(str(tmp_path), "test_connector_portfolio.json")
    engine = PaperTradingEngine(portfolio_file=test_portfolio_file)

    # Monkeypatch singleton getter for isolated test
    import tools.paper_trading as pt_module
    old_instance = pt_module._ENGINE_INSTANCE
    pt_module._ENGINE_INSTANCE = engine

    try:
        # 1. Check initial portfolio balance ($1,000,000.00)
        port = dispatch_tool("get_paper_portfolio", {})
        assert port["cash_balance"] == INITIAL_PORTFOLIO_CASH
        assert port["open_positions_count"] == 0

        # 2. Execute a buy order: 10 shares of MU @ $100.00 ($1,000.00 total)
        trade_res = dispatch_tool("execute_paper_trade", {
            "symbol": "MU",
            "asset_class": "Equities",
            "side": "BUY",
            "quantity": 10.0,
            "price": 100.0,
            "strategy_type": "Long Stock",
            "notes": "Connector test execution"
        })
        assert trade_res["success"] is True
        assert trade_res["trade"]["symbol"] == "MU"
        pos_id = trade_res["trade"]["position_id"]
        assert trade_res["remaining_cash"] == INITIAL_PORTFOLIO_CASH - 1000.0

        # 3. Verify portfolio reflects position
        port_updated = dispatch_tool("get_paper_portfolio", {})
        assert port_updated["open_positions_count"] == 1
        assert port_updated["positions"][0]["position_id"] == pos_id

        # 4. Close position at $110.00 (+10% gain -> $100.00 profit)
        close_res = dispatch_tool("close_paper_position", {
            "position_id": pos_id,
            "exit_price": 110.0,
            "reason": "Take Profit Target"
        })
        assert close_res["success"] is True
        assert close_res["closed_trade"]["realized_pnl"] == 100.0
        assert close_res["new_cash_balance"] == INITIAL_PORTFOLIO_CASH + 100.0

        # 5. Verify portfolio has zero open positions
        port_final = dispatch_tool("get_paper_portfolio", {})
        assert port_final["open_positions_count"] == 0
        assert port_final["total_realized_pnl"] == 100.0

    finally:
        pt_module._ENGINE_INSTANCE = old_instance


def test_mcp_tool_call_via_process_message():
    """Test executing tools/call via JSON-RPC protocol message."""
    call_msg = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "get_live_quote",
            "arguments": {"symbol": "AAPL"}
        }
    }
    response = process_message(call_msg)
    assert response["id"] == 10
    assert response["result"]["isError"] is False
    content_text = response["result"]["content"][0]["text"]
    parsed_content = json.loads(content_text)
    assert parsed_content["symbol"] == "AAPL"
    assert parsed_content["last_price"] > 0.0


def test_groq_offline_agent_dispatch():
    """Test Groq connector offline dispatch without requiring live API keys."""
    res = run_groq_agent(
        prompt="Resolve micron and get live price quote",
        api_key=None,
        verbose=False
    )
    assert res["mode"] == "offline_dispatch"
    assert len(res["tool_calls_executed"]) >= 1
    tool_names = [call["tool"] for call in res["tool_calls_executed"]]
    assert "resolve_ticker" in tool_names


def test_error_handling_invalid_tool_dispatch():
    """Test error handling when dispatching an unknown tool name."""
    with pytest.raises(ValueError) as excinfo:
        dispatch_tool("non_existent_tool_xyz", {})
    assert "Unknown tool" in str(excinfo.value)

    # Test via execute_tool_call wrapper (returns error dict)
    res = execute_tool_call("non_existent_tool_xyz", {})
    assert res.get("status") == "FAILED"
    assert "error" in res
