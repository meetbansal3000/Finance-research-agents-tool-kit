"""
tests/test_nvidia_skills_integration.py - Integration Tests for NVIDIA Skills
Tests the mathematical formulations and integration of:
1. cuopt-numerical-optimization-formulation (PortfolioQPOptimizer)
2. cuopt-routing-api-python (SupplyChainLogisticsOptimizer)
3. tilegym-cutile-autotuning (FinancialKernelAutotuner)
4. BacktestSandbox with QP optimization
5. ProvenanceLedger audit trails
"""

import os
import pytest
import numpy as np
from tools.calc.portfolio_opt import PortfolioQPOptimizer
from tools.calc.supply_chain_opt import SupplyChainLogisticsOptimizer
from tools.calc.gpu_autotune_sim import FinancialKernelAutotuner, _autotune_cache
from tools.ledger import ProvenanceLedger
from tools.backtest import BacktestSandbox


def test_qp_portfolio_optimizer_gmv_formulation():
    """Test Global Minimum Variance formulation under budget and bound constraints."""
    ledger = ProvenanceLedger(run_id="test_qp_gmv")
    opt = PortfolioQPOptimizer(risk_free_rate=0.04)
    tickers = ["AAPL", "MSFT", "NVDA", "AMZN"]
    
    cov = np.array([
        [0.040, 0.015, 0.020, 0.018],
        [0.015, 0.035, 0.019, 0.014],
        [0.020, 0.019, 0.060, 0.022],
        [0.018, 0.014, 0.022, 0.045]
    ])
    mu = np.array([0.15, 0.14, 0.25, 0.18])

    res = opt.solve_global_minimum_variance(tickers, cov, max_weight=0.40, expected_returns=mu, ledger=ledger)

    # Budget equality: sum of weights == 1.0
    weights = list(res["weights"].values())
    assert pytest.approx(sum(weights), abs=1e-3) == 1.0

    # Bounds: all weights >= 0 and <= max_weight (0.40)
    for w in weights:
        assert w >= -1e-5
        assert w <= 0.4001

    assert res["annualized_volatility"] > 0
    assert res["dual_budget_multiplier"] > 0
    assert res["formulation_type"] == "QP_GLOBAL_MINIMUM_VARIANCE"

    # Verify ProvenanceLedger entry
    assert "ledger_id" in res
    entry = ledger.get_entry(res["ledger_id"])
    assert entry is not None
    assert entry["source_tag"] == "QP_CALC"
    assert ledger.verify_entry_integrity(res["ledger_id"]) is True


def test_qp_portfolio_optimizer_mean_variance_target_return():
    """Test Mean-Variance formulation with target return and dual multipliers."""
    ledger = ProvenanceLedger(run_id="test_qp_mv")
    opt = PortfolioQPOptimizer()
    tickers = ["T1", "T2", "T3"]
    cov = np.array([
        [0.05, 0.01, 0.01],
        [0.01, 0.04, 0.01],
        [0.01, 0.01, 0.06]
    ])
    mu = np.array([0.10, 0.15, 0.20])

    res = opt.solve_mean_variance(
        tickers=tickers,
        cov_matrix=cov,
        expected_returns=mu,
        target_return=0.14,
        max_weight=0.60,
        ledger=ledger
    )

    weights = list(res["weights"].values())
    assert pytest.approx(sum(weights), abs=1e-3) == 1.0
    assert res["expected_return"] > 0.10
    assert "dual_return_multiplier" in res
    assert "dual_budget_multiplier" in res
    assert "ledger_id" in res
    assert ledger.verify_entry_integrity(res["ledger_id"]) is True


def test_qp_portfolio_psd_validation():
    """Test covariance matrix positive semi-definiteness detection."""
    opt = PortfolioQPOptimizer()
    pd_matrix = np.array([[1.0, 0.2], [0.2, 1.0]])
    is_psd, min_eig = opt.validate_covariance_matrix(pd_matrix)
    assert is_psd is True
    assert min_eig > 0

    with pytest.raises(ValueError):
        opt.validate_covariance_matrix(np.array([1.0, 2.0]))


def test_supply_chain_vrp_formulation():
    """Test Capacitated Vehicle Routing Problem (CVRP) solving and fuel margin elasticity."""
    ledger = ProvenanceLedger(run_id="test_vrp")
    coords = [(0, 0), (10, 10), (10, -10), (-10, 10), (-10, -10), (20, 0)]
    cost_matrix = SupplyChainLogisticsOptimizer.build_euclidean_cost_matrix(coords)
    demands = [0.0, 15.0, 20.0, 12.0, 18.0, 25.0]

    optimizer = SupplyChainLogisticsOptimizer(cost_per_distance_unit=2.0, fuel_cost_share=0.35)
    res = optimizer.solve_capacitated_vrp(
        cost_matrix=cost_matrix,
        demands=demands,
        vehicle_capacity=50.0,
        num_vehicles=3,
        ledger=ledger
    )

    assert res["num_routes"] <= 3
    assert res["total_network_distance"] > 0
    assert res["total_transport_cost"] > 0
    assert res["cost_per_unit_delivered"] > 0
    assert res["fleet_capacity_utilization_pct"] > 0

    # Verify each route starts and ends at depot (0) and satisfies capacity
    for route in res["routes"]:
        assert route["stops"][0] == 0
        assert route["stops"][-1] == 0
        assert route["load"] <= 50.0 + 1e-5

    # Check fuel price sensitivity
    sens = res["sensitivity"]
    assert sens["fuel_plus_10pct_cost"] > res["total_transport_cost"]
    assert sens["fuel_plus_20pct_cost"] > sens["fuel_plus_10pct_cost"]

    # Verify ledger provenance
    assert "ledger_id" in res
    assert ledger.verify_entry_integrity(res["ledger_id"]) is True


def test_supply_chain_infeasible_capacity_guard():
    """Test that optimizer flags demand exceeding total fleet capacity."""
    coords = [(0, 0), (5, 5)]
    cost_matrix = SupplyChainLogisticsOptimizer.build_euclidean_cost_matrix(coords)
    demands = [0.0, 100.0]

    optimizer = SupplyChainLogisticsOptimizer()
    with pytest.raises(ValueError, match="Infeasible demand"):
        optimizer.solve_capacitated_vrp(cost_matrix, demands, vehicle_capacity=20.0, num_vehicles=2)


def test_gpu_autotune_monte_carlo_tune_once_cache():
    """Test TileGym tune-once/cache/launch pattern and risk simulation."""
    ledger = ProvenanceLedger(run_id="test_autotune_mc")
    _autotune_cache.clear()
    tuner = FinancialKernelAutotuner()

    w = np.array([0.5, 0.5])
    mu = np.array([0.10, 0.12])
    cov = np.array([[0.04, 0.01], [0.01, 0.05]])

    # Call 1: Should benchmark search space and populate cache
    res1 = tuner.run_monte_carlo_portfolio_sim(w, mu, cov, num_simulations=1000, ledger=ledger)
    assert res1["selected_occupancy"] in [1, 2, 4, 8]
    assert res1["selected_block_size"] in [128, 256, 512, 1024]
    assert res1["was_cached"] is True
    # CVaR is more severe than or equal to VaR in tail losses
    assert res1["conditional_var_95_pct"] <= res1["value_at_risk_95_pct"]

    # Call 2: Immediate cache hit with zero benchmark overhead
    res2 = tuner.run_monte_carlo_portfolio_sim(w, mu, cov, num_simulations=1000, ledger=ledger)
    assert res2["was_cached"] is True
    assert res2["selected_occupancy"] == res1["selected_occupancy"]

    # Verify ledger provenance
    assert "ledger_id" in res1
    assert ledger.verify_entry_integrity(res1["ledger_id"]) is True


def test_gpu_autotune_disable_flag(monkeypatch):
    """Test DISABLE_AUTOTUNE=1 environment variable handling."""
    monkeypatch.setenv("DISABLE_AUTOTUNE", "1")
    tuner = FinancialKernelAutotuner()
    w = np.array([0.5, 0.5])
    mu = np.array([0.10, 0.12])
    cov = np.array([[0.04, 0.01], [0.01, 0.05]])

    res = tuner.run_monte_carlo_portfolio_sim(w, mu, cov, num_simulations=500)
    assert res["autotune_disabled"] is True
    assert res["was_cached"] is False
    assert res["selected_occupancy"] == 1


def test_backtest_with_qp_optimization(monkeypatch):
    """Test BacktestSandbox.run_optimized_portfolio_backtest with synthetic returns."""
    import pandas as pd
    
    dates = pd.date_range("2025-01-01", periods=100, freq="B")
    np.random.seed(42)
    # Generate prices
    aapl_prices = 150.0 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 100)))
    msft_prices = 300.0 * np.exp(np.cumsum(np.random.normal(0.0004, 0.012, 100)))
    spy_prices = 450.0 * np.exp(np.cumsum(np.random.normal(0.0003, 0.009, 100)))

    df = pd.DataFrame({
        "AAPL": aapl_prices,
        "MSFT": msft_prices,
        "SPY": spy_prices
    }, index=dates)

    # Mock yf.download to return MultiIndex DataFrame matching yfinance output
    import yfinance as yf
    def mock_download(tickers, *args, **kwargs):
        # Return DataFrame with top-level column "Close"
        sub_df = df[[t for t in tickers if t in df.columns]]
        res_df = pd.DataFrame(
            sub_df.values,
            index=sub_df.index,
            columns=pd.MultiIndex.from_tuples([("Close", col) for col in sub_df.columns])
        )
        return res_df

    monkeypatch.setattr(yf, "download", mock_download)

    sandbox = BacktestSandbox()
    summary = sandbox.run_optimized_portfolio_backtest(["AAPL", "MSFT"], benchmark="SPY", max_weight=0.70)

    assert "optimal_weights" in summary
    assert "AAPL" in summary["optimal_weights"]
    assert "MSFT" in summary["optimal_weights"]
    assert pytest.approx(sum(summary["optimal_weights"].values()), abs=1e-3) == 1.0
    assert summary["portfolio_return_pct"] is not None
    assert summary["sharpe_ratio"] is not None
