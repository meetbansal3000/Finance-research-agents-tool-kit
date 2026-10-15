"""
tests/test_walk_forward_backtest.py
Comprehensive unit test suite for:
1. WalkForwardSplitter: Zero lookahead bias rolling window generation.
2. calculate_institutional_metrics: Total Return, Benchmark Alpha, Sharpe, Sortino, Calmar, Max Drawdown & Duration, Profit Factor, Win Rate, TCA costs.
3. WalkForwardBacktester:
   - EquityMomentumVolFilter with 4-Moment Cornish-Fisher VaR stops & Half-Kelly sizing.
   - OptionsCreditSpreadCarry with POP_CF hurdle and multi-leg option TCA friction.
   - MeanVarianceQP with rolling Markowitz optimization & turnover friction.
4. AlgoOpportunityScanner:
   - Econometric moments estimation (Mean, Vol, Skew, Excess Kurtosis).
   - Positive expectancy condition (E[PnL] > 0, POP_CF >= 65%).
   - Committee gatekeeper approval and Half-Kelly allocation.
5. BacktestSandbox walk-forward integration.
"""

import math
import pytest
import numpy as np
import pandas as pd

from tools.calc.walk_forward_backtest import (
    WalkForwardSplitter,
    WalkForwardBacktester,
    AlgoOpportunityScanner,
    calculate_institutional_metrics
)
from tools.backtest import BacktestSandbox


def test_walk_forward_splitter():
    total_days = 360
    train_w = 180
    test_w = 60
    step = 60

    splits = WalkForwardSplitter.split(total_days, train_w, test_w, step)
    assert len(splits) >= 2

    for (tr_s, tr_e), (te_s, te_e) in splits:
        # Check window lengths
        assert tr_e - tr_s == train_w
        assert te_e - te_s == test_w
        # Strictly zero lookahead overlap: test starts exactly when train ends
        assert tr_e == te_s
        assert te_e <= total_days


def test_institutional_metrics_calculation():
    # Construct a sample equity curve with a known drawdown
    # Day 0: 100, Day 1: 110, Day 2: 99 (-10% DD), Day 3: 115, Day 4: 120
    portfolio = [100.0, 110.0, 99.0, 115.0, 120.0]
    benchmark = [100.0, 102.0, 104.0, 106.0, 110.0]
    pnls = [10.0, -11.0, 16.0, 5.0]
    tca = [1.50, 1.50, 1.50, 1.50]

    metrics = calculate_institutional_metrics(
        portfolio_series=portfolio,
        benchmark_series=benchmark,
        risk_free_rate_annual=0.0425,
        trade_pnls=pnls,
        tca_costs=tca
    )

    assert metrics["total_return_pct"] == 20.0
    assert metrics["benchmark_return_pct"] == 10.0
    assert metrics["alpha_pct"] == 10.0
    assert metrics["max_drawdown_pct"] == -10.0
    assert metrics["max_drawdown_duration_days"] >= 1
    assert metrics["total_trades"] == 4
    assert metrics["winning_trades"] == 3
    assert metrics["losing_trades"] == 1
    assert metrics["win_rate_pct"] == 75.0
    assert metrics["total_tca_cost_usd"] == 6.0
    assert metrics["profit_factor"] > 1.0
    assert "sharpe_ratio" in metrics
    assert "sortino_ratio" in metrics
    assert "calmar_ratio" in metrics


def test_equity_momentum_cf_filter_backtest():
    tester = WalkForwardBacktester(initial_capital=1000000.0)
    prices_df = tester.generate_synthetic_data(tickers=["AAPL", "MSFT"], days=360, seed=123)

    result = tester.run_equity_momentum_cf_filter(
        prices_df=prices_df,
        tickers=["AAPL"],
        benchmark="SPY",
        train_window=180,
        test_window=60,
        fast_ma=10,
        slow_ma=30
    )

    assert result["strategy"] == "EquityMomentumVolFilter"
    assert result["initial_capital_usd"] == 1000000.0
    assert result["ending_capital_usd"] > 0
    assert len(result["daily_equity"]) > 100
    assert len(result["daily_dates"]) == len(result["daily_equity"])

    m = result["metrics"]
    assert "total_return_pct" in m
    assert "sharpe_ratio" in m
    assert "sortino_ratio" in m
    assert "calmar_ratio" in m
    assert "max_drawdown_pct" in m
    assert m["total_tca_cost_usd"] >= 0.0

    wfe = result["walk_forward_efficiency"]
    assert "wfe_ratio" in wfe
    assert "robustness_verdict" in wfe
    assert len(result["windows"]) >= 2


def test_options_credit_spread_carry_backtest():
    tester = WalkForwardBacktester(initial_capital=1000000.0)
    prices_df = tester.generate_synthetic_data(tickers=["SPY", "QQQ"], days=360, seed=456)

    result = tester.run_options_credit_spread_carry(
        prices_df=prices_df,
        tickers=["SPY"],
        benchmark="SPY",
        train_window=180,
        test_window=60,
        target_delta=0.20,
        min_pop_cf=0.60
    )

    assert result["strategy"] == "OptionsCreditSpreadCarry"
    assert result["initial_capital_usd"] == 1000000.0
    assert result["ending_capital_usd"] > 0
    assert len(result["trades_log"]) >= 1

    m = result["metrics"]
    assert "total_return_pct" in m
    assert "win_rate_pct" in m
    assert m["total_tca_cost_usd"] > 0.0


def test_walk_forward_qp_portfolio_backtest():
    tester = WalkForwardBacktester(initial_capital=1000000.0)
    prices_df = tester.generate_synthetic_data(tickers=["AAPL", "MSFT", "GOOGL"], days=360, seed=789)

    result = tester.run_walk_forward_qp_portfolio(
        prices_df=prices_df,
        tickers=["AAPL", "MSFT", "GOOGL"],
        benchmark="SPY",
        train_window=180,
        test_window=60,
        max_weight=0.50
    )

    assert result["strategy"] == "MeanVarianceQP"
    assert result["initial_capital_usd"] == 1000000.0
    assert result["ending_capital_usd"] > 0
    assert len(result["windows"]) >= 2
    for win in result["windows"]:
        assert "weights" in win
        # Weights should sum to approx 100%
        total_w = sum(win["weights"].values())
        assert 95.0 <= total_w <= 105.0


def test_algo_opportunity_scanner():
    scanner = AlgoOpportunityScanner()
    res = scanner.scan_ticker("NVDA", lookback_days=90)

    assert res["ticker"] == "NVDA"
    assert res["spot_price"] > 0
    assert res["annualized_vol_pct"] > 0
    assert "skewness" in res
    assert "excess_kurtosis" in res
    assert "cf_var_99_daily_pct" in res
    assert res["pop_cf_pct"] >= 50.0
    assert res["half_kelly_allocation_pct"] > 0
    assert res["tca_cost_usd"] > 0
    assert res["committee_verdict"] in [
        "APPROVED", "REJECTED_NEGATIVE_EXPECTANCY", "REJECTED_EXCESS_TAIL_RISK"
    ]

    # Test universe scanning
    opps = scanner.scan_universe(tickers=["AAPL", "MSFT", "NVDA"], min_pop_cf=0.60)
    assert isinstance(opps, list)
    if opps:
        # Check sorted descending by expected PnL
        for i in range(len(opps) - 1):
            assert opps[i]["expected_pnl_usd"] >= opps[i + 1]["expected_pnl_usd"]


def test_backtest_sandbox_walk_forward_wrapper():
    sandbox = BacktestSandbox()
    res = sandbox.run_walk_forward_backtest(
        tickers=["AAPL"],
        strategy="EquityMomentumVolFilter",
        benchmark="SPY",
        train_window=180,
        test_window=60
    )
    assert "metrics" in res
    assert res["initial_capital_usd"] == 1000000.0
    assert "walk_forward_efficiency" in res

    opps = sandbox.scan_algo_opportunities(tickers=["AAPL", "MSFT"], min_pop_cf=0.60)
    assert isinstance(opps, list)
