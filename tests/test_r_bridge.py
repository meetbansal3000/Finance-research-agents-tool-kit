"""
tests/test_r_bridge.py - Unit and Integration Tests for RStudio & R Econometric Bridge
"""

import os
import pytest
from tools.r_bridge import RStudioBridge
from tools.ledger import ProvenanceLedger


def test_r_bridge_availability():
    bridge = RStudioBridge()
    assert bridge.is_available() is True
    res = bridge.execute_expression("cat(R.version.string)")
    assert res["success"] is True
    assert "4.6.1" in res["stdout"]


def test_r_bridge_monte_carlo_execution():
    bridge = RStudioBridge()
    ledger = ProvenanceLedger(run_id="test_r_ledger")

    mc_res = bridge.run_monte_carlo_dcf(
        base_fcf=100.0,
        shares_outstanding=10.0,
        net_debt=0.0,
        wacc_mean=0.09,
        wacc_sd=0.005,
        growth_mean=0.08,
        growth_sd=0.01,
        terminal_g=0.025,
        n_sim=250,
        ledger=ledger
    )

    assert "median_fair_value" in mc_res
    assert mc_res["median_fair_value"] > 0
    assert "quantiles" in mc_res
    assert mc_res["quantiles"]["5%"] < mc_res["quantiles"]["50%"] < mc_res["quantiles"]["95%"]
    assert mc_res["iterations"] == 250

    # Verify Provenance Ledger entry
    assert mc_res["ledger_id"] is not None
    entry = ledger.get_entry(mc_res["ledger_id"])
    assert entry["source_tag"] == "R_STUDIO_ECONOMETRICS"
    assert ledger.verify_entry_integrity(mc_res["ledger_id"]) is True


def test_r_agent_bridge_script():
    bridge = RStudioBridge()
    r_code = (
        "source('r_studio/agent_bridge.R'); "
        "res <- calc_dcf(base_fcf=50.0, growth_rates=c(0.05, 0.05), discount_rate=0.08, terminal_growth_rate=0.02, shares_outstanding=5.0); "
        "cat(sprintf('VAL:%.2f', res$result$fair_value_per_share))"
    )
    res = bridge.execute_expression(r_code)
    assert res["success"] is True
    assert "VAL:" in res["stdout"]


def test_r_portfolio_qp_execution():
    bridge = RStudioBridge()
    r_code = (
        "source('r_studio/agent_bridge.R'); "
        "cov <- matrix(c(0.04, 0.01, 0.01, 0.03), nrow=2); "
        "tickers <- c('AAPL', 'MSFT'); "
        "res <- solve_portfolio_qp(tickers, cov, max_weight=0.60); "
        "cat(sprintf('VOL:%.4f|SHARPE:%.2f', res$annualized_volatility, res$sharpe_ratio))"
    )
    res = bridge.execute_expression(r_code)
    assert res["success"] is True
    assert "VOL:" in res["stdout"]


def test_r_supply_chain_routing_execution():
    bridge = RStudioBridge()
    r_code = (
        "source('r_studio/agent_bridge.R'); "
        "cost_mat <- matrix(c(0, 10, 10, 0), nrow=2); "
        "demands <- c(0, 15); "
        "res <- solve_supply_chain_routing(cost_mat, demands, vehicle_capacity=50, num_vehicles=1); "
        "cat(sprintf('DIST:%.1f|COST:%.2f', res$total_network_distance, res$total_transport_cost))"
    )
    res = bridge.execute_expression(r_code)
    assert res["success"] is True
    assert "DIST:" in res["stdout"]

