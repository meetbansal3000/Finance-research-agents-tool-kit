"""
tools/backtest.py - Quantitative Screening & Backtesting Sandbox (Upgrade 10)
Implements Workflow 9 (Fundamental Screener) and historical portfolio backtesting simulation
against market benchmarks (S&P 500 / SPY).
Saves backtest reports and results to /backtests/.
"""

import os
import sys
import json
import datetime
from typing import Dict, Any, List, Optional
import numpy as np
import yfinance as yf
from tools.calc.portfolio_opt import PortfolioQPOptimizer

BACKTESTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backtests")

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "watchlist.txt")


class BacktestSandbox:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or BACKTESTS_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def screen_universe(
        self,
        tickers: List[str],
        min_op_margin: float = 0.20,
        max_debt_to_equity: float = 1.5,
        min_fcf_yield: float = 0.02
    ) -> Dict[str, Any]:
        """
        Fundamental multi-factor screen (Workflow 9).
        Filters universe on operating profitability, financial leverage, and cash generation.
        """
        results = []
        filter_stats = {
            "initial_universe": len(tickers),
            "passed_margin": 0,
            "passed_leverage": 0,
            "passed_all": 0
        }

        for ticker in tickers:
            clean_ticker = ticker.strip().upper()
            try:
                t = yf.Ticker(clean_ticker)
                info = t.info

                op_margin = float(info.get("operatingMargins") or 0.0)
                de_ratio = float(info.get("debtToEquity") or 0.0) / 100.0 if info.get("debtToEquity") else 0.5
                fcf = float(info.get("freeCashflow") or 0.0)
                mkt_cap = float(info.get("marketCap") or 1.0)
                f_yield = fcf / mkt_cap if mkt_cap > 0 else 0.0

                passes_margin = op_margin >= min_op_margin
                passes_leverage = de_ratio <= max_debt_to_equity
                passes_yield = f_yield >= min_fcf_yield

                if passes_margin:
                    filter_stats["passed_margin"] += 1
                if passes_margin and passes_leverage:
                    filter_stats["passed_leverage"] += 1

                passed = passes_margin and passes_leverage and passes_yield
                if passed:
                    filter_stats["passed_all"] += 1

                results.append({
                    "ticker": clean_ticker,
                    "company_name": info.get("shortName", clean_ticker),
                    "op_margin_pct": round(op_margin * 100.0, 2),
                    "debt_to_equity": round(de_ratio, 2),
                    "fcf_yield_pct": round(f_yield * 100.0, 2),
                    "passed": passed,
                    "reason_if_failed": (
                        "Low margin" if not passes_margin else (
                            "Elevated debt" if not passes_leverage else (
                                "Low FCF yield" if not passes_yield else "All criteria met"
                            )
                        )
                    )
                })
            except Exception:
                results.append({
                    "ticker": clean_ticker,
                    "company_name": clean_ticker,
                    "op_margin_pct": 0.0,
                    "debt_to_equity": 0.0,
                    "fcf_yield_pct": 0.0,
                    "passed": False,
                    "reason_if_failed": "Data fetch error"
                })

        return {
            "stats": filter_stats,
            "results": results,
            "qualified_tickers": [r["ticker"] for r in results if r["passed"]]
        }

    def run_portfolio_backtest(
        self,
        tickers: List[str],
        benchmark: str = "SPY",
        period: str = "1y"
    ) -> Dict[str, Any]:
        """
        Simulate equal-weighted portfolio return vs benchmark.
        Computes Sharpe ratio, Max Drawdown, Annualized Volatility, and Alpha.
        """
        all_symbols = list(set(tickers + [benchmark]))
        data = yf.download(all_symbols, period=period, progress=False)["Close"]

        if data.empty or benchmark not in data.columns:
            raise ValueError(f"Could not retrieve historical price series for {all_symbols}")

        returns = data.pct_change().dropna()

        # Equal-weighted portfolio returns
        portfolio_tickers = [t for t in tickers if t in returns.columns]
        if not portfolio_tickers:
            raise ValueError("No portfolio tickers found in downloaded price data.")

        port_returns = returns[portfolio_tickers].mean(axis=1)
        bench_returns = returns[benchmark]

        # Cumulative returns
        port_cum = (1 + port_returns).cumprod() - 1
        bench_cum = (1 + bench_returns).cumprod() - 1

        total_port_ret = float(port_cum.iloc[-1]) * 100.0
        total_bench_ret = float(bench_cum.iloc[-1]) * 100.0
        alpha = total_port_ret - total_bench_ret

        # Annualized volatility (assuming 252 trading days)
        port_vol = float(port_returns.std() * np.sqrt(252)) * 100.0
        bench_vol = float(bench_returns.std() * np.sqrt(252)) * 100.0

        # Sharpe ratio (assuming risk-free rate of 4.25%)
        rf_daily = 0.0425 / 252
        excess_daily = port_returns - rf_daily
        sharpe = float((excess_daily.mean() / port_returns.std()) * np.sqrt(252)) if port_returns.std() > 0 else 0.0

        # Maximum Drawdown
        cum_series = (1 + port_returns).cumprod()
        peak = cum_series.cummax()
        drawdown = (cum_series - peak) / peak
        max_drawdown = float(drawdown.min()) * 100.0

        summary = {
            "period": period,
            "tickers": portfolio_tickers,
            "benchmark": benchmark,
            "portfolio_return_pct": round(total_port_ret, 2),
            "benchmark_return_pct": round(total_bench_ret, 2),
            "alpha_pct": round(alpha, 2),
            "annualized_volatility_pct": round(port_vol, 2),
            "benchmark_volatility_pct": round(bench_vol, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_drawdown, 2)
        }

        # Save markdown report
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        report_path = os.path.join(self.output_dir, f"backtest_{date_str}.md")
        self._save_backtest_report(report_path, summary)

        return summary

    def run_optimized_portfolio_backtest(
        self,
        tickers: List[str],
        benchmark: str = "SPY",
        period: str = "1y",
        max_weight: float = 0.40,
        strategy: str = "min_variance"
    ) -> Dict[str, Any]:
        """
        Runs portfolio backtest with weights determined by NVIDIA cuOpt QP optimizer.
        Supports strategy="min_variance" (Global Minimum Variance) or strategy="mean_variance".
        """
        all_symbols = list(set(tickers + [benchmark]))
        data = yf.download(all_symbols, period=period, progress=False)["Close"]

        if data.empty or benchmark not in data.columns:
            raise ValueError(f"Could not retrieve historical price series for {all_symbols}")

        returns = data.pct_change().dropna()
        portfolio_tickers = [t for t in tickers if t in returns.columns]
        if not portfolio_tickers:
            raise ValueError("No portfolio tickers found in downloaded price data.")

        # Annualized covariance matrix and expected returns
        port_asset_returns = returns[portfolio_tickers]
        cov_matrix = port_asset_returns.cov().to_numpy() * 252
        mean_returns = port_asset_returns.mean().to_numpy() * 252

        # Solve QP via PortfolioQPOptimizer
        optimizer = PortfolioQPOptimizer()
        if strategy == "mean_variance":
            qp_sol = optimizer.solve_mean_variance(
                tickers=portfolio_tickers,
                cov_matrix=cov_matrix,
                expected_returns=mean_returns,
                max_weight=max_weight
            )
        else:
            qp_sol = optimizer.solve_global_minimum_variance(
                tickers=portfolio_tickers,
                cov_matrix=cov_matrix,
                max_weight=max_weight,
                expected_returns=mean_returns
            )

        weights_arr = np.array([qp_sol["weights"][t] for t in portfolio_tickers])

        # Compute weighted portfolio daily returns
        port_returns = port_asset_returns.dot(weights_arr)
        bench_returns = returns[benchmark]

        # Cumulative returns
        port_cum = (1 + port_returns).cumprod() - 1
        bench_cum = (1 + bench_returns).cumprod() - 1

        total_port_ret = float(port_cum.iloc[-1]) * 100.0
        total_bench_ret = float(bench_cum.iloc[-1]) * 100.0
        alpha = total_port_ret - total_bench_ret

        # Annualized volatility
        port_vol = float(port_returns.std() * np.sqrt(252)) * 100.0
        bench_vol = float(bench_returns.std() * np.sqrt(252)) * 100.0

        # Sharpe ratio (risk-free rate 4.25%)
        rf_daily = 0.0425 / 252
        excess_daily = port_returns - rf_daily
        sharpe = float((excess_daily.mean() / port_returns.std()) * np.sqrt(252)) if port_returns.std() > 0 else 0.0

        # Max drawdown
        cum_series = (1 + port_returns).cumprod()
        peak = cum_series.cummax()
        drawdown = (cum_series - peak) / peak
        max_drawdown = float(drawdown.min()) * 100.0

        # Extract per-asset price breakdown and dates
        start_date = str(data.index[0].date()) if hasattr(data.index[0], 'date') else str(data.index[0])[:10]
        end_date = str(data.index[-1].date()) if hasattr(data.index[-1], 'date') else str(data.index[-1])[:10]
        trading_days = len(data)

        asset_breakdown = []
        for t in portfolio_tickers:
            start_p = float(data[t].iloc[0])
            end_p = float(data[t].iloc[-1])
            ret_pct = ((end_p - start_p) / start_p) * 100.0 if start_p > 0 else 0.0
            w = float(qp_sol["weights"].get(t, 0.0))
            asset_breakdown.append({
                "ticker": t,
                "weight_pct": round(w * 100.0, 2),
                "start_price": round(start_p, 2),
                "end_price": round(end_p, 2),
                "asset_return_pct": round(ret_pct, 2),
                "weighted_return_pct": round(w * ret_pct, 2)
            })

        bench_start_p = float(data[benchmark].iloc[0])
        bench_end_p = float(data[benchmark].iloc[-1])

        summary = {
            "period": period,
            "tickers": portfolio_tickers,
            "benchmark": benchmark,
            "strategy": strategy,
            "optimal_weights": qp_sol["weights"],
            "qp_solution": qp_sol,
            "portfolio_return_pct": round(total_port_ret, 2),
            "benchmark_return_pct": round(total_bench_ret, 2),
            "alpha_pct": round(alpha, 2),
            "annualized_volatility_pct": round(port_vol, 2),
            "benchmark_volatility_pct": round(bench_vol, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "dates": [str(d.date()) if hasattr(d, 'date') else str(d)[:10] for d in port_cum.index],
            "portfolio_cum_trajectory": [round(float(v), 4) for v in (1 + port_cum).values],
            "benchmark_cum_trajectory": [round(float(v), 4) for v in (1 + bench_cum).values],
            "start_date": start_date,
            "end_date": end_date,
            "trading_days": trading_days,
            "asset_breakdown": asset_breakdown,
            "benchmark_start_price": round(bench_start_p, 2),
            "benchmark_end_price": round(bench_end_p, 2),
            "data_source": "Yahoo Finance (Live Market Feed)"
        }

        # Save markdown report
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        report_path = os.path.join(self.output_dir, f"backtest_optimized_{date_str}.md")
        self._save_backtest_report(report_path, summary)

        return summary

    def run_custom_portfolio_backtest(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        benchmark: str = "SPY",
        period: str = "1y"
    ) -> Dict[str, Any]:
        """
        Runs portfolio backtest with custom weights provided by the user.
        Normalizes weights to ensure sum = 1.0.
        """
        all_symbols = list(set(tickers + [benchmark]))
        data = yf.download(all_symbols, period=period, progress=False)["Close"]

        if data.empty or benchmark not in data.columns:
            raise ValueError(f"Could not retrieve historical price series for {all_symbols}")

        returns = data.pct_change().dropna()
        portfolio_tickers = [t for t in tickers if t in returns.columns]
        if not portfolio_tickers:
            raise ValueError("No portfolio tickers found in downloaded price data.")

        # Normalize provided weights across available tickers
        raw_w = np.array([float(weights.get(t, 1.0 / len(portfolio_tickers))) for t in portfolio_tickers])
        total_w = float(np.sum(raw_w))
        if total_w <= 0:
            norm_w = np.full(len(portfolio_tickers), 1.0 / len(portfolio_tickers))
        else:
            norm_w = raw_w / total_w

        weights_dict = {portfolio_tickers[i]: round(float(norm_w[i]), 4) for i in range(len(portfolio_tickers))}

        port_asset_returns = returns[portfolio_tickers]
        port_returns = port_asset_returns.dot(norm_w)
        bench_returns = returns[benchmark]

        # Cumulative returns
        port_cum = (1 + port_returns).cumprod() - 1
        bench_cum = (1 + bench_returns).cumprod() - 1

        total_port_ret = float(port_cum.iloc[-1]) * 100.0
        total_bench_ret = float(bench_cum.iloc[-1]) * 100.0
        alpha = total_port_ret - total_bench_ret

        # Annualized volatility
        port_vol = float(port_returns.std() * np.sqrt(252)) * 100.0
        bench_vol = float(bench_returns.std() * np.sqrt(252)) * 100.0

        # Sharpe ratio
        rf_daily = 0.0425 / 252
        excess_daily = port_returns - rf_daily
        sharpe = float((excess_daily.mean() / port_returns.std()) * np.sqrt(252)) if port_returns.std() > 0 else 0.0

        # Max drawdown
        cum_series = (1 + port_returns).cumprod()
        peak = cum_series.cummax()
        drawdown = (cum_series - peak) / peak
        max_drawdown = float(drawdown.min()) * 100.0

        start_date = str(data.index[0].date()) if hasattr(data.index[0], 'date') else str(data.index[0])[:10]
        end_date = str(data.index[-1].date()) if hasattr(data.index[-1], 'date') else str(data.index[-1])[:10]
        trading_days = len(data)

        asset_breakdown = []
        for i, t in enumerate(portfolio_tickers):
            start_p = float(data[t].iloc[0])
            end_p = float(data[t].iloc[-1])
            ret_pct = ((end_p - start_p) / start_p) * 100.0 if start_p > 0 else 0.0
            w = float(norm_w[i])
            asset_breakdown.append({
                "ticker": t,
                "weight_pct": round(w * 100.0, 2),
                "start_price": round(start_p, 2),
                "end_price": round(end_p, 2),
                "asset_return_pct": round(ret_pct, 2),
                "weighted_return_pct": round(w * ret_pct, 2)
            })

        bench_start_p = float(data[benchmark].iloc[0])
        bench_end_p = float(data[benchmark].iloc[-1])

        summary = {
            "period": period,
            "tickers": portfolio_tickers,
            "benchmark": benchmark,
            "strategy": "custom_user_allocation",
            "optimal_weights": weights_dict,
            "portfolio_return_pct": round(total_port_ret, 2),
            "benchmark_return_pct": round(total_bench_ret, 2),
            "alpha_pct": round(alpha, 2),
            "annualized_volatility_pct": round(port_vol, 2),
            "benchmark_volatility_pct": round(bench_vol, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "dates": [str(d.date()) if hasattr(d, 'date') else str(d)[:10] for d in port_cum.index],
            "portfolio_cum_trajectory": [round(float(v), 4) for v in (1 + port_cum).values],
            "benchmark_cum_trajectory": [round(float(v), 4) for v in (1 + bench_cum).values],
            "start_date": start_date,
            "end_date": end_date,
            "trading_days": trading_days,
            "asset_breakdown": asset_breakdown,
            "benchmark_start_price": round(bench_start_p, 2),
            "benchmark_end_price": round(bench_end_p, 2),
            "data_source": "Yahoo Finance (Live Market Feed)"
        }
        return summary


    def run_walk_forward_backtest(
        self,
        tickers: List[str],
        strategy: str = "EquityMomentumVolFilter",
        benchmark: str = "SPY",
        train_window: int = 180,
        test_window: int = 60,
        initial_capital: float = 1000000.0
    ) -> Dict[str, Any]:
        """
        Institutional Walk-Forward Backtest simulation with realistic TCA friction,
        Cornish-Fisher VaR stops, and Half-Kelly position sizing.
        """
        from tools.calc.walk_forward_backtest import WalkForwardBacktester
        tester = WalkForwardBacktester(initial_capital=initial_capital)

        # Download historical data from Yahoo Finance or generate synthetic fallback
        all_syms = list(set(tickers + [benchmark]))
        try:
            raw_data = yf.download(all_syms, period="2y", progress=False)["Close"]
            if raw_data.empty or (len(raw_data) < (train_window + test_window)):
                prices_df = tester.generate_synthetic_data(tickers=all_syms, days=360)
            else:
                prices_df = raw_data.dropna()
        except Exception:
            prices_df = tester.generate_synthetic_data(tickers=all_syms, days=360)

        if strategy == "OptionsCreditSpreadCarry":
            res = tester.run_options_credit_spread_carry(
                prices_df=prices_df,
                tickers=tickers,
                benchmark=benchmark,
                train_window=train_window,
                test_window=test_window
            )
        elif strategy == "MeanVarianceQP":
            res = tester.run_walk_forward_qp_portfolio(
                prices_df=prices_df,
                tickers=tickers,
                benchmark=benchmark,
                train_window=train_window,
                test_window=test_window
            )
        else:
            # Default: EquityMomentumVolFilter
            res = tester.run_equity_momentum_cf_filter(
                prices_df=prices_df,
                tickers=tickers,
                benchmark=benchmark,
                train_window=train_window,
                test_window=test_window
            )

        # Save institutional walk-forward markdown report
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        report_path = os.path.join(self.output_dir, f"walk_forward_{strategy.lower()}_{date_str}.md")
        self._save_walk_forward_report(report_path, res)
        return res

    def scan_algo_opportunities(
        self,
        tickers: Optional[List[str]] = None,
        min_pop_cf: float = 0.65
    ) -> List[Dict[str, Any]]:
        """
        Autonomous Strategy Scanner filtering for positive econometric expectancy (E[PnL] > 0, POP_CF >= 65%).
        """
        from tools.calc.walk_forward_backtest import AlgoOpportunityScanner
        scanner = AlgoOpportunityScanner(output_dir=self.output_dir)
        return scanner.scan_universe(tickers=tickers, min_pop_cf=min_pop_cf)

    def _save_walk_forward_report(self, filepath: str, results: Dict[str, Any]):
        m = results.get("metrics", {})
        wfe = results.get("walk_forward_efficiency", {})
        lines = [
            "# Institutional Walk-Forward Backtest Report",
            f"**Strategy:** `{results.get('strategy')}`  ",
            f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Portfolio Tickers:** {', '.join(results.get('tickers', []))}  ",
            f"**Benchmark:** {results.get('benchmark')}  ",
            f"**Initial Capital:** ${results.get('initial_capital_usd', 1000000.0):,.2f}  ",
            f"**Ending Capital:** ${results.get('ending_capital_usd', 0.0):,.2f}  ",
            "",
            "---",
            "",
            "### 📊 Institutional Performance Metrics",
            "| Performance Metric | Portfolio Result | Benchmark Result | Alpha / Delta |",
            "| :--- | :--- | :--- | :--- |",
            f"| Total Return | **{m.get('total_return_pct', 0.0):+.2f}%** | {m.get('benchmark_return_pct', 0.0):+.2f}% | **{m.get('alpha_pct', 0.0):+.2f}%** |",
            f"| Annualized Volatility | {m.get('annualized_volatility_pct', 0.0):.2f}% | N/A | Risk |",
            f"| Downside Deviation | {m.get('downside_deviation_pct', 0.0):.2f}% | N/A | Semideviation (Rf=4.25%) |",
            f"| Sharpe Ratio (Rf=4.25%) | **{m.get('sharpe_ratio', 0.0):.2f}** | N/A | Risk-adjusted return |",
            f"| Sortino Ratio | **{m.get('sortino_ratio', 0.0):.2f}** | N/A | Downside-adjusted return |",
            f"| Calmar Ratio | **{m.get('calmar_ratio', 0.0):.2f}** | N/A | Return to Max Drawdown |",
            f"| Maximum Drawdown | **{m.get('max_drawdown_pct', 0.0):.2f}%** | N/A | Peak-to-trough decline |",
            f"| Max Drawdown Duration | **{m.get('max_drawdown_duration_days', 0)} days** | N/A | Underwater recovery period |",
            f"| Profit Factor | **{m.get('profit_factor', 0.0):.2f}** | N/A | Gross Profit / Gross Loss |",
            f"| Win Rate % | **{m.get('win_rate_pct', 0.0):.1f}%** | N/A | ({m.get('winning_trades', 0)}/{m.get('total_trades', 0)} trades) |",
            f"| Total TCA Friction Paid | **${m.get('total_tca_cost_usd', 0.0):,.2f}** | N/A | Spread + Impact + Fees |",
            "",
            "---",
            "",
            "### 🔬 Walk-Forward Out-of-Sample Robustness",
            f"- **In-Sample Avg Sharpe:** `{wfe.get('in_sample_avg_sharpe', 0.0):.2f}`",
            f"- **Out-of-Sample Avg Sharpe:** `{wfe.get('out_of_sample_avg_sharpe', 0.0):.2f}`",
            f"- **Walk-Forward Efficiency (WFE):** `{wfe.get('wfe_ratio', 0.0):.2f}` ({wfe.get('robustness_verdict', 'N/A')})",
            "",
            "---",
            "*Generated by Institutional WalkForwardBacktest Sandbox.*"
        ]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _save_backtest_report(self, filepath: str, summary: Dict[str, Any]):
        lines = [
            f"# Quantitative Backtest Simulation Report",
            f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Tested Portfolio:** {', '.join(summary['tickers'])}  ",
            f"**Benchmark:** {summary['benchmark']}  ",
            f"**Simulation Window:** {summary['period']}  ",
            "",
            "---",
            "",
            "### 📊 Performance Summary",
            "| Performance Metric | Portfolio Result | Benchmark Result | Delta / Alpha |",
            "| :--- | :--- | :--- | :--- |",
            f"| Total Return | **{summary['portfolio_return_pct']:+.2f}%** | {summary['benchmark_return_pct']:+.2f}% | **{summary['alpha_pct']:+.2f}%** |",
            f"| Annualized Volatility | {summary['annualized_volatility_pct']:.2f}% | {summary['benchmark_volatility_pct']:.2f}% | {summary['annualized_volatility_pct'] - summary['benchmark_volatility_pct']:+.2f}% |",
            f"| Sharpe Ratio (Rf=4.25%) | **{summary['sharpe_ratio']:.2f}** | N/A | Risk-adjusted return |",
            f"| Maximum Drawdown | **{summary['max_drawdown_pct']:.2f}%** | N/A | Peak-to-trough decline |",
            "",
            "---",
            "*Generated by BacktestSandbox Engine.*"
        ]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


if __name__ == "__main__":
    sandbox = BacktestSandbox()
    screen_res = sandbox.screen_universe(["AAPL", "MSFT", "GOOGL", "NVDA"])
    print(f"Screen complete: {len(screen_res['qualified_tickers'])} stocks passed all criteria.")
    if screen_res["qualified_tickers"]:
        bt_res = sandbox.run_portfolio_backtest(screen_res["qualified_tickers"], period="1y")
        print(f"Backtest complete: Portfolio Return: {bt_res['portfolio_return_pct']}%, Alpha: {bt_res['alpha_pct']}%")
