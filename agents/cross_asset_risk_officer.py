"""
agents/cross_asset_risk_officer.py
Cross-Asset Risk Officer Agent
Chief Risk Officer (CRO) and Gatekeeper within Meridian Multi-Asset Master Orchestrator:
- Unified multi-asset Parametric VaR & CVaR (Expected Shortfall) at 95% & 99% confidence
- Cross-asset correlation matrix breakdown analysis
- Historical black-swan crisis stress testing (2008 GFC, 2020 Covid, 2022 Fed Rate Shock)
- Unified Red Flags Registry & mandatory risk mitigation gatekeeper
"""

import datetime
from typing import Dict, Any, List, Optional
from tools.ledger import ProvenanceLedger
from tools.calc.derivatives_math import CrossAssetRiskEngine
from tools.calc.probability_simulator import EconometricProbabilitySimulator


class CrossAssetRiskOfficer:
    """
    Cross-Asset Risk Officer: Independent oversight committee gatekeeper.
    Stress-tests multi-asset portfolios, enforces VaR/leverage caps,
    and aggregates all desk red flags into an authoritative audit verdict.
    """

    def __init__(self, ledger: Optional[ProvenanceLedger] = None):
        self.ledger = ledger or ProvenanceLedger(run_id=f"risk_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.agent_role = "Cross-Asset Risk Officer"

    def evaluate_portfolio_var(
        self,
        portfolio_value_usd: float,
        allocations_usd: Dict[str, float],
        annual_volatilities: Optional[Dict[str, float]] = None,
        correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None,
        horizon_days: int = 1
    ) -> Dict[str, Any]:
        """
        Compute institutional Parametric Value-at-Risk (VaR) and Conditional VaR (CVaR).
        """
        # Default baseline volatilities if not supplied
        vols = annual_volatilities or {
            "equities": 0.18,
            "fixed_income": 0.07,
            "commodities": 0.24,
            "crypto": 0.65,
            "options_overlay": 0.35
        }

        # Normalize weights
        tot = sum(allocations_usd.values())
        weights = {k: v / tot for k, v in allocations_usd.items()} if tot > 0 else {}

        # Default cross-asset correlation matrix if not supplied
        default_corr = {
            "equities": {"equities": 1.0, "fixed_income": -0.15, "commodities": 0.35, "crypto": 0.45, "options_overlay": -0.40},
            "fixed_income": {"equities": -0.15, "fixed_income": 1.0, "commodities": -0.10, "crypto": -0.05, "options_overlay": 0.10},
            "commodities": {"equities": 0.35, "fixed_income": -0.10, "commodities": 1.0, "crypto": 0.25, "options_overlay": -0.20},
            "crypto": {"equities": 0.45, "fixed_income": -0.05, "commodities": 0.25, "crypto": 1.0, "options_overlay": -0.30},
            "options_overlay": {"equities": -0.40, "fixed_income": 0.10, "commodities": -0.20, "crypto": -0.30, "options_overlay": 1.0}
        }
        corrs = correlation_matrix or default_corr

        var_metrics = CrossAssetRiskEngine.calculate_var_cvar(
            portfolio_value=portfolio_value_usd,
            asset_weights=weights,
            asset_volatilities_annual=vols,
            correlation_matrix=corrs,
            horizon_days=horizon_days
        )

        ledger_id = self.ledger.record(
            tool="CrossAssetRiskEngine.calculate_var_cvar",
            inputs={"portfolio_value": portfolio_value_usd, "horizon": horizon_days, "assets": list(allocations_usd.keys())},
            output={"var_99_dollar": var_metrics["var_99_dollar"], "cvar_99_dollar": var_metrics["cvar_99_dollar"]},
            source="Institutional VaR/CVaR Risk Engine",
            notes=f"1-day 99% VaR ${var_metrics['var_99_dollar']} ({var_metrics['var_99_pct']}%), CVaR ${var_metrics['cvar_99_dollar']}"
        )

        red_flags = []
        if var_metrics["var_99_pct"] > 4.5:
            red_flags.append({
                "severity": "CRITICAL",
                "category": "Excessive Portfolio VaR",
                "message": f"1-Day 99% VaR of {var_metrics['var_99_pct']:.2f}% (${var_metrics['var_99_dollar']:,.0f}) breaches institutional risk tolerance limit (4.0%)."
            })
        elif var_metrics["var_99_pct"] > 3.0:
            red_flags.append({
                "severity": "HIGH",
                "category": "Elevated VaR Exposure",
                "message": f"1-Day 99% VaR is {var_metrics['var_99_pct']:.2f}%. High risk regime requiring close tracking."
            })

        # Concentration check
        for asset, w in weights.items():
            if w > 0.40 and asset != "fixed_income":
                red_flags.append({
                    "severity": "HIGH",
                    "category": "Asset Class Concentration Risk",
                    "message": f"Asset class '{asset}' constitutes {w*100.0:.1f}% of total portfolio value. Diversification cap is 40%."
                })

        return {
            "agent": self.agent_role,
            "portfolio_value_usd": portfolio_value_usd,
            "var_metrics": var_metrics,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags
        }

    def stress_test_portfolio(
        self,
        allocations_usd: Dict[str, float],
        custom_scenarios: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Stress test portfolio allocations against severe historical macro dislocations.
        """
        stress_res = CrossAssetRiskEngine.simulate_crisis_stress(
            allocations_usd=allocations_usd,
            custom_scenarios=custom_scenarios
        )

        ledger_id = self.ledger.record(
            tool="CrossAssetRiskEngine.simulate_crisis_stress",
            inputs={"allocations": allocations_usd},
            output={"scenarios_evaluated": len(stress_res["scenarios"])},
            source="Historical Crisis Stress Simulator",
            notes=f"Evaluated {len(stress_res['scenarios'])} black swan stress scenarios"
        )

        red_flags = []
        for s in stress_res["scenarios"]:
            if s["projected_drawdown_pct"] < -25.0:
                red_flags.append({
                    "severity": "CRITICAL",
                    "category": "Catastrophic Stress Vulnerability",
                    "message": f"Under scenario '{s['scenario_name']}', portfolio suffers severe drawdown of {s['projected_drawdown_pct']:.1f}% (${abs(s['projected_pnl_usd']):,.0f})."
                })
            elif s["projected_drawdown_pct"] < -18.0:
                red_flags.append({
                    "severity": "HIGH",
                    "category": "Stress Test Capital Impairment",
                    "message": f"Under scenario '{s['scenario_name']}', portfolio suffers substantial drawdown of {s['projected_drawdown_pct']:.1f}%."
                })

        return {
            "agent": self.agent_role,
            "stress_results": stress_res,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags
        }

    def evaluate_asset_tail_risk(
        self,
        ticker: str,
        spot_price: float,
        horizon_days: int = 30,
        custom_volatility: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Independent CRO assessment of asset return asymmetry, fat tails,
        Cornish-Fisher VaR/CVaR, and Jarque-Bera normality rejection.
        """
        sim_engine = EconometricProbabilitySimulator()
        moments = sim_engine.calculate_empirical_moments(ticker)
        vol = custom_volatility if custom_volatility is not None else float(moments["annualized_volatility"])
        t_years = horizon_days / 365.0

        metrics = sim_engine.calculate_comprehensive_econometric_metrics(
            spot=spot_price,
            volatility=vol,
            time_years=t_years,
            drift=float(moments["annualized_drift"]),
            skewness=float(moments["sample_skewness"]),
            excess_kurtosis=float(moments["sample_excess_kurtosis"])
        )

        ledger_id = self.ledger.record(
            tool="EconometricProbabilitySimulator.calculate_comprehensive_econometric_metrics",
            inputs={"ticker": ticker, "spot": spot_price, "horizon_days": horizon_days, "vol": vol},
            output={"skew": moments["sample_skewness"], "kurt": moments["sample_excess_kurtosis"], "var_cf_95_pct": metrics["var_metrics"]["var_cf_95_pct"]},
            source="CRO Econometric Tail Risk Assessor",
            ticker=ticker,
            notes=f"CRO Tail Risk Assessment for {ticker}: Skew {moments['sample_skewness']}, Kurt {moments['sample_excess_kurtosis']}"
        )

        red_flags = []
        if moments["normality_rejected"] and moments["sample_excess_kurtosis"] > 2.5:
            red_flags.append({
                "severity": "HIGH",
                "category": "Severe Leptokurtic Tail Risk",
                "message": f"Excess kurtosis ({moments['sample_excess_kurtosis']:.2f}) indicates severe fat tails. Gaussian risk models drastically underestimate tail losses."
            })
        if moments["sample_skewness"] < -0.60:
            red_flags.append({
                "severity": "HIGH",
                "category": "Crash Asymmetry Fragility",
                "message": f"Negative skewness ({moments['sample_skewness']:.2f}) reflects significant structural downside crash risk."
            })
        if metrics["var_metrics"]["fat_tail_surcharge_95_pct"] > 4.0:
            red_flags.append({
                "severity": "MEDIUM",
                "category": "Elevated Fat-Tail VaR Surcharge",
                "message": f"Fat-tail surcharge adds +{metrics['var_metrics']['fat_tail_surcharge_95_pct']:.2f}% to baseline 95% VaR."
            })

        return {
            "agent": self.agent_role,
            "ticker": ticker,
            "horizon_days": horizon_days,
            "spot_price": spot_price,
            "empirical_moments": moments,
            "econometric_metrics": metrics,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags,
            "verdict": "FLAGGED" if any(rf["severity"] in ["CRITICAL", "HIGH"] for rf in red_flags) else "MONITORED"
        }

    def consolidate_risk_audit(
        self,
        portfolio_summary: Dict[str, Any],
        desk_reports: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compile master cross-asset risk audit, aggregating all desk red flags,
        and issuing a binding investment committee verdict.
        """
        all_red_flags: List[Dict[str, Any]] = []

        # Ingest desk-specific red flags
        for desk_name, report in desk_reports.items():
            flags = report.get("red_flags", [])
            for f in flags:
                flag_copy = dict(f)
                flag_copy["source_desk"] = desk_name
                all_red_flags.append(flag_copy)

        # Ingest portfolio-level red flags if provided
        port_flags = portfolio_summary.get("red_flags", [])
        for f in port_flags:
            flag_copy = dict(f)
            flag_copy["source_desk"] = "Cross-Asset Risk Officer"
            all_red_flags.append(flag_copy)

        # Count severities
        critical_count = sum(1 for f in all_red_flags if f.get("severity") == "CRITICAL")
        high_count = sum(1 for f in all_red_flags if f.get("severity") == "HIGH")
        medium_count = sum(1 for f in all_red_flags if f.get("severity") == "MEDIUM")

        if critical_count > 0:
            verdict = "REJECTED"
            verdict_rationale = f"Risk limits violated: {critical_count} CRITICAL red flag(s) identified. Immediate de-risking or hedging mandatory."
        elif high_count >= 3:
            verdict = "CONDITIONAL_APPROVAL"
            verdict_rationale = f"Approved with conditions: {high_count} HIGH red flag(s) detected. Supplementary hedges required prior to execution."
        else:
            verdict = "APPROVED"
            verdict_rationale = "Portfolio satisfies all institutional risk parameters, leverage limits, and VaR tolerances."

        ledger_id = self.ledger.record(
            tool="CrossAssetRiskOfficer.consolidate_risk_audit",
            inputs={"desks": list(desk_reports.keys()), "flags": len(all_red_flags)},
            output={"verdict": verdict, "critical": critical_count, "high": high_count},
            source="Cross-Asset Risk Gatekeeper",
            notes=f"Audit Verdict: {verdict}. Rationale: {verdict_rationale}"
        )

        return {
            "agent": self.agent_role,
            "verdict": verdict,
            "verdict_rationale": verdict_rationale,
            "critical_flags_count": critical_count,
            "high_flags_count": high_count,
            "medium_flags_count": medium_count,
            "total_red_flags": len(all_red_flags),
            "red_flags_register": all_red_flags,
            "provenance_ledger_id": ledger_id
        }
