"""
tools/trading_analytics.py - Institutional Paper Trading Performance Analytics

Calculates institutional-grade execution analytics for closed paper trades:
1. Return vs a chosen benchmark (SPY, QQQ, etc.) with alpha / excess return.
2. Peak-to-trough Maximum Drawdown (% and $).
3. Hit rate (win rate %) across all closed trades.
4. Average win and average loss ($ and %).
5. Statistical trading expectancy ($ per trade and risk ratio).
6. Total number of trades (winning, losing, breakeven).
7. Non-parametric bootstrap confidence intervals (mean return, hit rate, expectancy).
8. Explicit warning banner when fewer than 30 trades have been recorded.
"""

import os
import datetime
import numpy as np
import yfinance as yf
from typing import Dict, Any, List, Optional, Tuple, Union


class TradingAnalytics:
    """
    Quantitative trading performance and statistical expectancy calculator
    with non-parametric bootstrapping and benchmark attribution.
    """

    MIN_TRADES_THRESHOLD: int = 30

    @classmethod
    def calculate_analytics(
        cls,
        closed_trades: List[Dict[str, Any]],
        initial_capital: float = 100000.0,
        current_equity: Optional[float] = None,
        benchmark: str = "SPY",
        benchmark_return_pct: Optional[float] = None,
        n_bootstraps: int = 1000,
        confidence_level: float = 0.95,
        random_seed: Optional[int] = None,
        min_trades_threshold: int = MIN_TRADES_THRESHOLD
    ) -> Dict[str, Any]:
        """
        Compute full statistical analytics suite across closed trading history.
        """
        init_cap = float(initial_capital) if initial_capital and initial_capital > 0 else 100000.0
        n_trades = len(closed_trades)

        # 1. Trade Classification & Win/Loss Metrics
        pnls: List[float] = []
        pnl_pcts: List[float] = []
        winning_pnls: List[float] = []
        losing_pnls: List[float] = []
        winning_pcts: List[float] = []
        losing_pcts: List[float] = []

        for t in closed_trades:
            pnl = float(t.get("realized_pnl", 0.0))
            cost = float(t.get("cost_basis", 0.0))
            if "realized_pnl_pct" in t and t["realized_pnl_pct"] is not None:
                ret_pct = float(t["realized_pnl_pct"])
            elif cost > 0:
                ret_pct = (pnl / cost) * 100.0
            else:
                ret_pct = 0.0

            pnls.append(pnl)
            pnl_pcts.append(ret_pct)

            if pnl > 0:
                winning_pnls.append(pnl)
                winning_pcts.append(ret_pct)
            elif pnl < 0:
                losing_pnls.append(pnl)
                losing_pcts.append(ret_pct)

        n_wins = len(winning_pnls)
        n_losses = len(losing_pnls)
        n_breakeven = n_trades - n_wins - n_losses

        total_realized_pnl = round(sum(pnls), 2)
        hit_rate_pct = round((n_wins / n_trades) * 100.0, 2) if n_trades > 0 else 0.0

        avg_win_usd = round(float(np.mean(winning_pnls)), 2) if winning_pnls else 0.0
        avg_loss_usd = round(float(np.mean(losing_pnls)), 2) if losing_pnls else 0.0
        avg_win_pct = round(float(np.mean(winning_pcts)), 2) if winning_pcts else 0.0
        avg_loss_pct = round(float(np.mean(losing_pcts)), 2) if losing_pcts else 0.0

        if avg_loss_usd != 0:
            win_loss_ratio = round(abs(avg_win_usd / avg_loss_usd), 2)
        else:
            win_loss_ratio = float("inf") if avg_win_usd > 0 else 0.0

        # 2. Expectancy Calculation
        # E = (Win Rate * Avg Win) + (Loss Rate * Avg Loss) [where Avg Loss is negative]
        if n_trades > 0:
            expectancy_usd = round(float(np.mean(pnls)), 2)
            if avg_loss_usd != 0:
                win_prob = n_wins / n_trades
                loss_prob = n_losses / n_trades
                expectancy_ratio = round((win_prob * (abs(avg_win_usd) / abs(avg_loss_usd))) - loss_prob, 2)
            else:
                expectancy_ratio = round(1.0, 2) if avg_win_usd > 0 else 0.0
        else:
            expectancy_usd = 0.0
            expectancy_ratio = 0.0

        # 3. Equity Curve & Maximum Drawdown
        equity_series = [init_cap]
        running_eq = init_cap
        for pnl in pnls:
            running_eq += pnl
            equity_series.append(running_eq)

        # Include current open equity if specified
        if current_equity is not None and float(current_equity) > 0:
            latest_eq = float(current_equity)
            if abs(latest_eq - running_eq) > 0.01:
                equity_series.append(latest_eq)
        else:
            latest_eq = running_eq

        peaks = [equity_series[0]]
        for eq in equity_series[1:]:
            peaks.append(max(peaks[-1], eq))

        drawdowns_pct = []
        drawdowns_usd = []
        for eq, peak in zip(equity_series, peaks):
            if peak > 0:
                dd_pct = ((eq - peak) / peak) * 100.0
                dd_usd = eq - peak
            else:
                dd_pct = 0.0
                dd_usd = 0.0
            drawdowns_pct.append(dd_pct)
            drawdowns_usd.append(dd_usd)

        max_drawdown_pct = round(float(min(drawdowns_pct)), 2) if drawdowns_pct else 0.0
        max_drawdown_usd = round(float(min(drawdowns_usd)), 2) if drawdowns_usd else 0.0

        # 4. Total Return & Benchmark Comparison
        portfolio_return_pct = round(((latest_eq - init_cap) / init_cap) * 100.0, 2)

        resolved_bm_return = cls._resolve_benchmark_return(
            benchmark=benchmark,
            closed_trades=closed_trades,
            override_return=benchmark_return_pct
        )
        alpha_pct = round(portfolio_return_pct - resolved_bm_return, 2)

        # 5. Bootstrap Confidence Intervals
        bootstrap_results = cls._compute_bootstrap_ci(
            pnls=pnls,
            n_bootstraps=n_bootstraps,
            confidence_level=confidence_level,
            random_seed=random_seed
        )

        # 6. Sample Size Warning (< 30 trades)
        has_warning = n_trades < min_trades_threshold
        if has_warning:
            warning_msg = (
                f"⚠️ SAMPLE SIZE WARNING: Only {n_trades} closed trade(s) recorded (< {min_trades_threshold} threshold). "
                f"Hit rates, trading expectancy, and bootstrap confidence intervals have high standard errors "
                f"and lack statistical significance until at least {min_trades_threshold} trades are logged."
            )
        else:
            warning_msg = None

        return {
            "number_of_trades": n_trades,
            "winning_trades": n_wins,
            "losing_trades": n_losses,
            "breakeven_trades": n_breakeven,
            "total_realized_pnl": total_realized_pnl,
            "hit_rate_pct": hit_rate_pct,
            "average_win_usd": avg_win_usd,
            "average_loss_usd": avg_loss_usd,
            "average_win_pct": avg_win_pct,
            "average_loss_pct": avg_loss_pct,
            "win_loss_ratio": win_loss_ratio,
            "expectancy_usd": expectancy_usd,
            "expectancy_ratio": expectancy_ratio,
            "initial_capital": init_cap,
            "final_equity": round(latest_eq, 2),
            "portfolio_return_pct": portfolio_return_pct,
            "benchmark_symbol": benchmark.upper(),
            "benchmark_return_pct": resolved_bm_return,
            "alpha_pct": alpha_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "max_drawdown_usd": max_drawdown_usd,
            "equity_curve": [round(x, 2) for x in equity_series],
            "bootstrap_ci": bootstrap_results,
            "has_sample_size_warning": has_warning,
            "sample_size_warning_message": warning_msg,
            "min_trades_threshold": min_trades_threshold
        }

    @classmethod
    def _resolve_benchmark_return(
        cls,
        benchmark: str,
        closed_trades: List[Dict[str, Any]],
        override_return: Optional[float] = None
    ) -> float:
        """Resolve benchmark return, either via override or live historical query."""
        if override_return is not None:
            return round(float(override_return), 2)

        bm_clean = (benchmark or "SPY").strip().upper()
        if not closed_trades:
            return 0.0

        try:
            # Determine evaluation date range
            dates: List[datetime.date] = []
            for t in closed_trades:
                for date_key in ("opened_at", "closed_at"):
                    raw_val = t.get(date_key)
                    if raw_val:
                        try:
                            # Strip time portion if present
                            clean_dt = str(raw_val)[:10]
                            dates.append(datetime.date.fromisoformat(clean_dt))
                        except Exception:
                            pass

            if dates:
                start_date = min(dates) - datetime.timedelta(days=7)
                t_obj = yf.Ticker(bm_clean)
                hist = t_obj.history(start=start_date.isoformat(), interval="1d")
                if not hist.empty and len(hist) >= 2:
                    start_px = float(hist["Close"].iloc[0])
                    end_px = float(hist["Close"].iloc[-1])
                    if start_px > 0:
                        ret = ((end_px - start_px) / start_px) * 100.0
                        return round(ret, 2)
        except Exception:
            pass

        return 0.0

    @classmethod
    def _compute_bootstrap_ci(
        cls,
        pnls: List[float],
        n_bootstraps: int = 1000,
        confidence_level: float = 0.95,
        random_seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Non-parametric bootstrap confidence intervals for mean PnL, hit rate, and expectancy.
        """
        n = len(pnls)
        if n < 2:
            return {
                "available": False,
                "reason": "Insufficient closed trades for bootstrap estimation (requires N >= 2)."
            }

        pnl_arr = np.array(pnls, dtype=np.float64)
        rng = np.random.default_rng(random_seed)

        boot_mean_pnls = np.empty(n_bootstraps)
        boot_hit_rates = np.empty(n_bootstraps)

        for b in range(n_bootstraps):
            sample = rng.choice(pnl_arr, size=n, replace=True)
            boot_mean_pnls[b] = np.mean(sample)
            boot_hit_rates[b] = (np.count_nonzero(sample > 0) / n) * 100.0

        alpha = 1.0 - confidence_level
        lower_pct = (alpha / 2.0) * 100.0
        upper_pct = (1.0 - (alpha / 2.0)) * 100.0

        mean_pnl_ci = (
            round(float(np.percentile(boot_mean_pnls, lower_pct)), 2),
            round(float(np.percentile(boot_mean_pnls, upper_pct)), 2)
        )
        hit_rate_ci = (
            round(float(np.percentile(boot_hit_rates, lower_pct)), 2),
            round(float(np.percentile(boot_hit_rates, upper_pct)), 2)
        )

        return {
            "available": True,
            "confidence_level": confidence_level,
            "n_bootstraps": n_bootstraps,
            "mean_pnl_usd": {
                "lower": mean_pnl_ci[0],
                "upper": mean_pnl_ci[1],
                "median": round(float(np.median(boot_mean_pnls)), 2)
            },
            "hit_rate_pct": {
                "lower": hit_rate_ci[0],
                "upper": hit_rate_ci[1],
                "median": round(float(np.median(boot_hit_rates)), 2)
            },
            "expectancy_usd": {
                "lower": mean_pnl_ci[0],
                "upper": mean_pnl_ci[1],
                "median": round(float(np.median(boot_mean_pnls)), 2)
            }
        }
