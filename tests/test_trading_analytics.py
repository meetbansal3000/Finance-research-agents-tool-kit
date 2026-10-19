"""
tests/test_trading_analytics.py - Unit Tests for Trading Analytics Suite

Verifies:
1. Return vs chosen benchmark and alpha attribution.
2. Maximum drawdown (% and $) across equity trajectory.
3. Hit rate (win rate) percentage.
4. Average win and average loss ($ and %).
5. Statistical trading expectancy ($ and ratio).
6. Total number of trades (winning, losing, breakeven).
7. Non-parametric bootstrap confidence intervals (mean PnL, hit rate, expectancy).
8. Clear sample size warning when fewer than 30 trades are logged.
"""

import pytest
import numpy as np
import tempfile
import os
from tools.trading_analytics import TradingAnalytics
from tools.paper_trading import PaperTradingEngine


def test_trading_analytics_worked_example():
    """
    Worked Example with 10 trades (6 wins, 4 losses):
    Wins:  [+$500, +$1200, +$800, +$450, +$1500, +$750]  -> Sum = $5,200, Mean = $866.67
    Losses: [-$300, -$600, -$400, -$500]                 -> Sum = -$1,800, Mean = -$450.00
    Net Realized PnL: $5,200 - $1,800 = +$3,400.00
    Total Trades = 10
    Hit Rate = 6 / 10 = 60.0%
    Average Win = $866.67
    Average Loss = -$450.00
    Win/Loss Ratio = 866.67 / 450.00 = 1.93
    Expectancy = (0.60 * 866.67) + (0.40 * -450.00) = +$340.00 / trade
    Initial Capital = $100,000
    Final Equity = $103,400
    Portfolio Return = +3.40%
    Benchmark Return = +2.00% -> Alpha = +1.40%
    Sample size < 30 -> has_sample_size_warning is True
    """
    trades = [
        {"position_id": "T1", "symbol": "AAPL", "realized_pnl": 500.0, "cost_basis": 10000.0, "realized_pnl_pct": 5.0},
        {"position_id": "T2", "symbol": "MSFT", "realized_pnl": -300.0, "cost_basis": 10000.0, "realized_pnl_pct": -3.0},
        {"position_id": "T3", "symbol": "NVDA", "realized_pnl": 1200.0, "cost_basis": 12000.0, "realized_pnl_pct": 10.0},
        {"position_id": "T4", "symbol": "GOOGL", "realized_pnl": -600.0, "cost_basis": 15000.0, "realized_pnl_pct": -4.0},
        {"position_id": "T5", "symbol": "AMZN", "realized_pnl": 800.0, "cost_basis": 10000.0, "realized_pnl_pct": 8.0},
        {"position_id": "T6", "symbol": "TSLA", "realized_pnl": 450.0, "cost_basis": 9000.0, "realized_pnl_pct": 5.0},
        {"position_id": "T7", "symbol": "AMD", "realized_pnl": -400.0, "cost_basis": 8000.0, "realized_pnl_pct": -5.0},
        {"position_id": "T8", "symbol": "INTC", "realized_pnl": 1500.0, "cost_basis": 15000.0, "realized_pnl_pct": 10.0},
        {"position_id": "T9", "symbol": "META", "realized_pnl": -500.0, "cost_basis": 10000.0, "realized_pnl_pct": -5.0},
        {"position_id": "T10", "symbol": "NFLX", "realized_pnl": 750.0, "cost_basis": 7500.0, "realized_pnl_pct": 10.0},
    ]

    metrics = TradingAnalytics.calculate_analytics(
        closed_trades=trades,
        initial_capital=100000.0,
        benchmark="SPY",
        benchmark_return_pct=2.0,
        n_bootstraps=2000,
        random_seed=42
    )

    # Core statistics verification
    assert metrics["number_of_trades"] == 10
    assert metrics["winning_trades"] == 6
    assert metrics["losing_trades"] == 4
    assert metrics["breakeven_trades"] == 0
    assert metrics["hit_rate_pct"] == 60.0
    assert metrics["total_realized_pnl"] == 3400.0
    assert metrics["average_win_usd"] == 866.67
    assert metrics["average_loss_usd"] == -450.00
    assert metrics["win_loss_ratio"] == 1.93
    assert metrics["expectancy_usd"] == 340.00
    assert metrics["expectancy_ratio"] == round((0.60 * 1.93) - 0.40, 2)  # (0.60 * 1.93) - 0.40 = 0.76

    # Return & benchmark attribution
    assert metrics["initial_capital"] == 100000.0
    assert metrics["final_equity"] == 103400.0
    assert metrics["portfolio_return_pct"] == 3.40
    assert metrics["benchmark_symbol"] == "SPY"
    assert metrics["benchmark_return_pct"] == 2.00
    assert metrics["alpha_pct"] == 1.40

    # Sample size warning (< 30 trades)
    assert metrics["has_sample_size_warning"] is True
    assert "SAMPLE SIZE WARNING" in metrics["sample_size_warning_message"]
    assert "Only 10 closed trade(s) recorded" in metrics["sample_size_warning_message"]

    # Bootstrap confidence intervals
    b_ci = metrics["bootstrap_ci"]
    assert b_ci["available"] is True
    assert b_ci["confidence_level"] == 0.95
    assert b_ci["mean_pnl_usd"]["lower"] <= b_ci["mean_pnl_usd"]["median"] <= b_ci["mean_pnl_usd"]["upper"]
    assert b_ci["hit_rate_pct"]["lower"] <= b_ci["hit_rate_pct"]["median"] <= b_ci["hit_rate_pct"]["upper"]


def test_max_drawdown_worked_example():
    """
    Explicit Equity Trajectory:
    Start: $100,000
    T1: +$10,000 -> $110,000 (Peak = $110,000, DD = 0%)
    T2: -$11,000 -> $99,000  (Peak = $110,000, DD = -$11,000 / $110,000 = -10.00%)
    T3: +$2,000  -> $101,000 (Peak = $110,000, DD = -$9,000 / $110,000 = -8.18%)
    T4: -$11,000 -> $90,000  (Peak = $110,000, DD = -$20,000 / $110,000 = -18.18%)
    T5: +$30,000 -> $120,000 (New Peak = $120,000, DD = 0%)

    Expected Maximum Drawdown:
    max_drawdown_pct = -18.18%
    max_drawdown_usd = -$20,000.00
    """
    trades = [
        {"realized_pnl": 10000.0},
        {"realized_pnl": -11000.0},
        {"realized_pnl": 2000.0},
        {"realized_pnl": -11000.0},
        {"realized_pnl": 30000.0},
    ]

    metrics = TradingAnalytics.calculate_analytics(
        closed_trades=trades,
        initial_capital=100000.0
    )

    assert metrics["max_drawdown_pct"] == -18.18
    assert metrics["max_drawdown_usd"] == -20000.00
    assert metrics["equity_curve"] == [100000.0, 110000.0, 99000.0, 101000.0, 90000.0, 120000.0]


def test_sample_size_warning_cleared_at_thirty_trades():
    """
    Verifies that the warning is active at 29 trades and cleared at 30 trades.
    """
    # 29 trades: Warning must be ACTIVE
    trades_29 = [{"realized_pnl": 100.0} for _ in range(29)]
    m_29 = TradingAnalytics.calculate_analytics(closed_trades=trades_29)
    assert m_29["has_sample_size_warning"] is True
    assert m_29["sample_size_warning_message"] is not None
    assert "Only 29 closed trade(s)" in m_29["sample_size_warning_message"]

    # 30 trades: Warning must be CLEARED
    trades_30 = [{"realized_pnl": 100.0} for _ in range(30)]
    m_30 = TradingAnalytics.calculate_analytics(closed_trades=trades_30)
    assert m_30["has_sample_size_warning"] is False
    assert m_30["sample_size_warning_message"] is None


def test_zero_trades_graceful_handling():
    """
    With 0 trades, should report zero metrics cleanly without division by zero.
    """
    metrics = TradingAnalytics.calculate_analytics(closed_trades=[], initial_capital=50000.0)
    assert metrics["number_of_trades"] == 0
    assert metrics["winning_trades"] == 0
    assert metrics["losing_trades"] == 0
    assert metrics["hit_rate_pct"] == 0.0
    assert metrics["expectancy_usd"] == 0.0
    assert metrics["portfolio_return_pct"] == 0.0
    assert metrics["max_drawdown_pct"] == 0.0
    assert metrics["has_sample_size_warning"] is True
    assert metrics["bootstrap_ci"]["available"] is False


def test_paper_trading_engine_get_analytics_integration():
    """
    Verifies PaperTradingEngine.get_analytics() end-to-end integration.
    """
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        t_path = f.name
    if os.path.exists(t_path):
        os.remove(t_path)

    try:
        engine = PaperTradingEngine(
            portfolio_file=t_path,
            initial_capital=50000.0,
            enforce_journal_gate=False
        )

        # Execute and close 2 trades
        engine.execute_trade(symbol="AAPL", asset_class="Equities", side="BUY", quantity=10.0, price=100.0)
        positions = engine.load_portfolio()["positions"]
        assert len(positions) == 1
        pos_id = positions[0]["position_id"]
        # Close with profit: $120 exit -> +$200 profit
        engine.close_position(position_id=pos_id, exit_price=120.0, reason="Target Reached")

        engine.execute_trade(symbol="MSFT", asset_class="Equities", side="BUY", quantity=10.0, price=200.0)
        positions = engine.load_portfolio()["positions"]
        pos_id_2 = positions[0]["position_id"]
        # Close with loss: $190 exit -> -$100 loss
        engine.close_position(position_id=pos_id_2, exit_price=190.0, reason="Stop Hit")

        analytics = engine.get_analytics(benchmark="SPY", benchmark_return_pct=1.0)
        assert analytics["number_of_trades"] == 2
        assert analytics["winning_trades"] == 1
        assert analytics["losing_trades"] == 1
        assert analytics["hit_rate_pct"] == 50.0
        assert analytics["total_realized_pnl"] == 100.0  # +200 - 100
        assert analytics["average_win_usd"] == 200.0
        assert analytics["average_loss_usd"] == -100.0
        assert analytics["expectancy_usd"] == 50.0  # (200 - 100) / 2
        assert analytics["has_sample_size_warning"] is True
        assert analytics["bootstrap_ci"]["available"] is True
    finally:
        if os.path.exists(t_path):
            os.remove(t_path)
