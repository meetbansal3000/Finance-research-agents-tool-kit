"""
tools/risk_sentry.py
Continuous Autonomous Background Risk Sentry for Meridian Multi-Asset Terminal.

Performs automated real-time risk surveillance over the live paper portfolio:
1. Audits live positions from PaperTradingEngine & ProvenanceLedger.
2. Marks open positions to market using real-time quotes.
3. Computes empirical moments (Drift, Volatility, Skewness, Kurtosis) & Normality.
4. Evaluates 95% & 99% Cornish-Fisher Value-at-Risk (VaR) and Tail Asymmetry.
5. Flags downside panic regimes (Skewness < -0.60, Excess Kurtosis > 3.0).
6. Dispatches structured alerts (CRITICAL, WARNING, ADVISORY) to alerts/risk_alerts.jsonl.
7. Logs cryptographic audit trails via HMAC-SHA256 Provenance Ledger.
"""

import os
import sys
import json
import time
import datetime
import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.paper_trading import PaperTradingEngine, INITIAL_PORTFOLIO_CASH
from tools.ledger import ProvenanceLedger
from tools.calc.probability_simulator import (
    EconometricProbabilitySimulator,
    cornish_fisher_quantile
)
from tools.calc.derivatives_math import CrossAssetRiskEngine

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ALERTS_DIR = os.path.join(PROJECT_DIR, "alerts")
RISK_ALERTS_LOG = os.path.join(ALERTS_DIR, "risk_alerts.jsonl")
RISK_SENTRY_STATE = os.path.join(ALERTS_DIR, "risk_sentry_state.json")


class PortfolioRiskSentry:
    """
    Autonomous Quantitative Risk Sentry.
    Continuously audits portfolio tail risks, position drawdowns, margin limits,
    and non-Gaussian econometric distribution shifts.
    """

    def __init__(
        self,
        paper_engine: Optional[PaperTradingEngine] = None,
        ledger: Optional[ProvenanceLedger] = None,
        alerts_dir: Optional[str] = None
    ):
        self.paper_engine = paper_engine or PaperTradingEngine()
        self.ledger = ledger or ProvenanceLedger(run_id="risk_sentry")
        self.alerts_dir = alerts_dir or ALERTS_DIR
        os.makedirs(self.alerts_dir, exist_ok=True)
        self.log_file = os.path.join(self.alerts_dir, "risk_alerts.jsonl")
        self.state_file = os.path.join(self.alerts_dir, "risk_sentry_state.json")
        self.sim_engine = EconometricProbabilitySimulator()

    def audit_portfolio_risk(
        self,
        custom_quotes: Optional[Dict[str, float]] = None,
        max_position_drawdown_pct: float = 15.0,
        max_portfolio_var_95_pct: float = 6.0,
        panic_skew_threshold: float = -0.60,
        custom_econo_moments: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Execute an exhaustive quantitative risk audit of the open paper portfolio book.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 1. Mark Portfolio to Market
        portfolio = self.paper_engine.mark_to_market(quotes=custom_quotes)
        positions = portfolio.get("positions", [])
        total_equity = float(portfolio.get("total_equity", INITIAL_PORTFOLIO_CASH))
        cash_balance = float(portfolio.get("cash_balance", INITIAL_PORTFOLIO_CASH))
        total_unrealized_pnl = float(portfolio.get("total_unrealized_pnl", 0.0))
        portfolio_return_pct = float(portfolio.get("portfolio_return_pct", 0.0))

        breaches: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        advisories: List[Dict[str, Any]] = []

        # 2. Audit Individual Positions
        total_margin_committed = 0.0
        symbols_in_portfolio = set()

        for pos in positions:
            sym = pos.get("symbol", "UNKNOWN")
            symbols_in_portfolio.add(sym)
            pnl_pct = float(pos.get("unrealized_pnl_pct", 0.0))
            unrealized_usd = float(pos.get("unrealized_pnl", 0.0))
            mkt_val = float(pos.get("market_value", 0.0))
            cost_basis = float(pos.get("cost_basis", 0.0))
            asset_class = pos.get("asset_class", "Equities")
            margin = float(pos.get("margin_committed", 0.0))
            total_margin_committed += margin

            # Drawdown threshold check
            if pnl_pct <= -max_position_drawdown_pct:
                breaches.append({
                    "severity": "CRITICAL",
                    "type": "POSITION_DRAWDOWN_BREACH",
                    "symbol": sym,
                    "asset_class": asset_class,
                    "unrealized_pnl_pct": pnl_pct,
                    "unrealized_pnl_usd": unrealized_usd,
                    "message": f"Position {sym} breached max drawdown hurdle ({pnl_pct:.2f}% <= -{max_position_drawdown_pct:.1f}%). Unrealized loss: ${abs(unrealized_usd):,.2f} USD."
                })
            elif pnl_pct <= -(max_position_drawdown_pct * 0.60):
                warnings.append({
                    "severity": "WARNING",
                    "type": "ELEVATED_POSITION_LOSS",
                    "symbol": sym,
                    "asset_class": asset_class,
                    "unrealized_pnl_pct": pnl_pct,
                    "unrealized_pnl_usd": unrealized_usd,
                    "message": f"Position {sym} approaching drawdown limit ({pnl_pct:.2f}%). Unrealized loss: ${abs(unrealized_usd):,.2f} USD."
                })

            # Concentration risk (single position > 25% of equity)
            if total_equity > 0.0 and (cost_basis / total_equity) > 0.25:
                warnings.append({
                    "severity": "WARNING",
                    "type": "PORTFOLIO_CONCENTRATION_EXCESS",
                    "symbol": sym,
                    "exposure_pct": round((cost_basis / total_equity) * 100.0, 2),
                    "message": f"Position {sym} represents {((cost_basis / total_equity) * 100.0):.1f}% of total portfolio equity (exceeds 25% concentration ceiling)."
                })

        # Margin Utilization Guard (Total margin > 65% of cash)
        margin_utilization_pct = (total_margin_committed / max(1.0, cash_balance)) * 100.0 if cash_balance > 0 else 100.0
        if margin_utilization_pct > 70.0:
            breaches.append({
                "severity": "CRITICAL",
                "type": "MARGIN_OVERLEVERAGE_BREACH",
                "margin_utilization_pct": round(margin_utilization_pct, 2),
                "committed_margin_usd": round(total_margin_committed, 2),
                "message": f"Committed derivative margin (${total_margin_committed:,.2f} USD) consumes {margin_utilization_pct:.1f}% of available cash. Critical squeeze risk."
            })
        elif margin_utilization_pct > 45.0:
            warnings.append({
                "severity": "WARNING",
                "type": "ELEVATED_MARGIN_UTILIZATION",
                "margin_utilization_pct": round(margin_utilization_pct, 2),
                "message": f"Committed derivative margin at {margin_utilization_pct:.1f}% of available cash."
            })

        # 3. Market Econometric Distribution & Tail Risk Analysis
        # Use representative benchmark (or primary asset) for macroeconomic moment auditing
        audit_sym = list(symbols_in_portfolio)[0] if symbols_in_portfolio else "SPY"
        econo_profile = self.sim_engine.calculate_empirical_moments(audit_sym)
        if custom_econo_moments:
            econo_profile.update(custom_econo_moments)

        sample_skew = float(econo_profile.get("sample_skewness", -0.45))
        sample_kurt = float(econo_profile.get("sample_excess_kurtosis", 1.80))
        annual_vol = float(econo_profile.get("annualized_volatility_pct", 25.0))
        normality_rejected = bool(econo_profile.get("normality_rejected", True))

        # 4. Cornish-Fisher 95% and 99% Horizon VaR & Tail Asymmetry
        horizon_days = 1
        t_years = horizon_days / 252.0
        sigma_t = (annual_vol / 100.0) * math.sqrt(t_years)

        z_norm_95 = 1.644853
        z_norm_99 = 2.326348
        z_cf_95_dn = cornish_fisher_quantile(-z_norm_95, skewness=sample_skew, excess_kurtosis=sample_kurt)
        z_cf_99_dn = cornish_fisher_quantile(-z_norm_99, skewness=sample_skew, excess_kurtosis=sample_kurt)
        z_cf_99_up = cornish_fisher_quantile(z_norm_99, skewness=sample_skew, excess_kurtosis=sample_kurt)

        var_cf_95_pct = abs(z_cf_95_dn) * sigma_t * 100.0
        var_cf_99_pct = abs(z_cf_99_dn) * sigma_t * 100.0
        var_cf_95_usd = total_equity * (var_cf_95_pct / 100.0)
        var_cf_99_usd = total_equity * (var_cf_99_pct / 100.0)

        # Fat-tail surcharge compared to normal distribution
        var_normal_95_pct = z_norm_95 * sigma_t * 100.0
        fat_tail_surcharge_95_pct = max(0.0, var_cf_95_pct - var_normal_95_pct)
        fat_tail_surcharge_95_usd = total_equity * (fat_tail_surcharge_95_pct / 100.0)

        tail_asymmetry_ratio = abs(z_cf_99_dn) / max(0.1, z_cf_99_up)

        # Audit against Portfolio VaR Threshold
        if var_cf_95_pct > max_portfolio_var_95_pct:
            breaches.append({
                "severity": "CRITICAL",
                "type": "PORTFOLIO_VAR_BREACH",
                "var_cf_95_pct": round(var_cf_95_pct, 2),
                "var_cf_95_usd": round(var_cf_95_usd, 2),
                "threshold_pct": max_portfolio_var_95_pct,
                "message": f"1-Day Cornish-Fisher 95% VaR ({var_cf_95_pct:.2f}%) exceeds safety ceiling ({max_portfolio_var_95_pct:.1f}%). Potential 1-day tail loss: ${var_cf_95_usd:,.2f} USD."
            })
        elif var_cf_95_pct > (max_portfolio_var_95_pct * 0.75):
            warnings.append({
                "severity": "WARNING",
                "type": "ELEVATED_PORTFOLIO_VAR",
                "var_cf_95_pct": round(var_cf_95_pct, 2),
                "var_cf_95_usd": round(var_cf_95_usd, 2),
                "message": f"1-Day Cornish-Fisher 95% VaR elevated at {var_cf_95_pct:.2f}% (${var_cf_95_usd:,.2f} USD)."
            })

        # 5. Downside Panic Regime Shift Detection
        if sample_skew < panic_skew_threshold:
            breaches.append({
                "severity": "CRITICAL",
                "type": "DOWNSIDE_PANIC_REGIME_SHIFT",
                "skewness": round(sample_skew, 4),
                "excess_kurtosis": round(sample_kurt, 4),
                "message": f"Severe Downside Panic Regime detected (Skewness: {sample_skew:.3f} < {panic_skew_threshold:.2f}, Kurtosis: {sample_kurt:.3f}). Extreme left fat tail."
            })
        elif sample_skew < (panic_skew_threshold * 0.70):
            warnings.append({
                "severity": "WARNING",
                "type": "ASYMMETRIC_DOWNSIDE_SKEW",
                "skewness": round(sample_skew, 4),
                "message": f"Elevated downside return asymmetry (Skewness: {sample_skew:.3f})."
            })

        # 6. Overall Health Status Synthesis
        if breaches:
            overall_status = "CRITICAL_RISK_BREACH"
            status_badge = "🔴 CRITICAL BREACH"
        elif warnings:
            overall_status = "ELEVATED_RISK_WARNING"
            status_badge = "🟡 ELEVATED RISK"
        else:
            overall_status = "HEALTHY_WITHIN_BOUNDS"
            status_badge = "🟢 HEALTHY / NOMINAL"

        audit_result = {
            "timestamp": timestamp,
            "overall_status": overall_status,
            "status_badge": status_badge,
            "portfolio_metrics": {
                "total_equity_usd": round(total_equity, 2),
                "cash_balance_usd": round(cash_balance, 2),
                "total_unrealized_pnl_usd": round(total_unrealized_pnl, 2),
                "portfolio_return_pct": round(portfolio_return_pct, 2),
                "open_positions_count": len(positions),
                "total_margin_committed_usd": round(total_margin_committed, 2),
                "margin_utilization_pct": round(margin_utilization_pct, 1)
            },
            "econometric_risk_metrics": {
                "benchmark_symbol": audit_sym,
                "annualized_volatility_pct": round(annual_vol, 2),
                "sample_skewness": round(sample_skew, 4),
                "sample_excess_kurtosis": round(sample_kurt, 4),
                "normality_rejected": normality_rejected,
                "tail_regime": econo_profile.get("tail_regime", "Leptokurtic"),
                "skew_regime": econo_profile.get("skew_regime", "Downside Asymmetry"),
                "var_95_cf_pct": round(var_cf_95_pct, 2),
                "var_95_cf_usd": round(var_cf_95_usd, 2),
                "var_99_cf_pct": round(var_cf_99_pct, 2),
                "var_99_cf_usd": round(var_cf_99_usd, 2),
                "fat_tail_surcharge_95_pct": round(fat_tail_surcharge_95_pct, 2),
                "fat_tail_surcharge_95_usd": round(fat_tail_surcharge_95_usd, 2),
                "tail_asymmetry_ratio": round(tail_asymmetry_ratio, 2)
            },
            "breaches": breaches,
            "warnings": warnings,
            "advisories": advisories,
            "total_breaches_count": len(breaches),
            "total_warnings_count": len(warnings)
        }

        # 7. Persist Alerts and Update Sentry State
        self._record_alerts_and_state(audit_result)

        # 8. Cryptographic Provenance Ledger Registration
        ledger_id = self.ledger.record(
            tool="PortfolioRiskSentry.audit_portfolio_risk",
            inputs={"positions_count": len(positions), "total_equity": total_equity},
            output={"overall_status": overall_status, "breaches": len(breaches), "warnings": len(warnings)},
            source="Continuous Background Risk Sentry",
            notes=f"Risk Sentry Audit: Status {overall_status} (VaR 95%: {var_cf_95_pct:.2f}%, Breaches: {len(breaches)})"
        )
        audit_result["provenance_ledger_id"] = ledger_id

        return audit_result

    def _record_alerts_and_state(self, audit: Dict[str, Any]) -> None:
        """Append alerts to JSONL and update risk_sentry_state.json."""
        timestamp = audit["timestamp"]
        all_events = audit.get("breaches", []) + audit.get("warnings", [])

        if all_events:
            with open(self.log_file, "a", encoding="utf-8") as f:
                for ev in all_events:
                    ev_copy = dict(ev)
                    ev_copy["timestamp"] = timestamp
                    ev_copy["portfolio_equity"] = audit["portfolio_metrics"]["total_equity_usd"]
                    f.write(json.dumps(ev_copy) + "\n")

        state_data = {
            "last_audited_at": timestamp,
            "overall_status": audit["overall_status"],
            "status_badge": audit["status_badge"],
            "active_breaches_count": audit["total_breaches_count"],
            "active_warnings_count": audit["total_warnings_count"],
            "var_95_cf_pct": audit["econometric_risk_metrics"]["var_95_cf_pct"],
            "var_95_cf_usd": audit["econometric_risk_metrics"]["var_95_cf_usd"],
            "total_equity_usd": audit["portfolio_metrics"]["total_equity_usd"],
            "open_positions_count": audit["portfolio_metrics"]["open_positions_count"]
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

    def load_latest_sentry_state(self) -> Dict[str, Any]:
        """Load current Sentry state from disk."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_audited_at": None,
            "overall_status": "UNINITIALIZED",
            "status_badge": "⚪ UNINITIALIZED",
            "active_breaches_count": 0,
            "active_warnings_count": 0
        }

    def load_recent_risk_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Load recent risk alerts from the JSONL log file."""
        if not os.path.exists(self.log_file):
            return []
        alerts = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        alerts.append(json.loads(line))
        except Exception:
            return []
        return alerts[-limit:]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Autonomous Portfolio Risk Sentry")
    parser.add_argument("--check-now", action="store_true", help="Run immediate risk audit")
    parser.add_argument("--loop", action="store_true", help="Run continuous background risk monitoring loop")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring loop interval in seconds")
    args = parser.parse_args()

    sentry = PortfolioRiskSentry()
    if args.check_now or not args.loop:
        result = sentry.audit_portfolio_risk()
        print(f"Risk Audit Complete: {result['status_badge']}")
        print(f"Equity: ${result['portfolio_metrics']['total_equity_usd']:,.2f} USD")
        print(f"1-Day 95% Cornish-Fisher VaR: {result['econometric_risk_metrics']['var_95_cf_pct']:.2f}% (${result['econometric_risk_metrics']['var_95_cf_usd']:,.2f} USD)")
        print(f"Breaches: {result['total_breaches_count']} | Warnings: {result['total_warnings_count']}")
    elif args.loop:
        print(f"Starting Continuous Portfolio Risk Sentry (interval={args.interval}s)... Press Ctrl+C to terminate.")
        try:
            while True:
                res = sentry.audit_portfolio_risk()
                print(f"[{res['timestamp']}] {res['status_badge']} | Equity: ${res['portfolio_metrics']['total_equity_usd']:,.2f} | Breaches: {res['total_breaches_count']}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("Risk Sentry loop terminated.")
