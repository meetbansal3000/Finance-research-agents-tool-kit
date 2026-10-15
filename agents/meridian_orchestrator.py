"""
agents/meridian_orchestrator.py
Meridian Multi-Asset Master Orchestrator
Central command and multi-agent coordination engine for:
1. Options Greek Strategist
2. Futures & Commodity Desk Agent
3. Fixed Income Macro Agent
4. Crypto & 24/7 Derivatives Agent
5. Cross-Asset Risk Officer

Synthesizes cross-asset research dossiers, enforces risk gatekeeping,
records all analytical facts in the cryptographic provenance ledger,
and compiles institutional investment committee memorandums with full red flags.
"""

import datetime
from typing import Dict, Any, List, Optional
from tools.ledger import ProvenanceLedger
from agents.options_greek_agent import OptionsGreekStrategist
from agents.futures_commodity_agent import FuturesCommodityAgent
from agents.fixed_income_macro_agent import FixedIncomeMacroAgent
from agents.crypto_derivatives_agent import CryptoDerivativesAgent
from agents.cross_asset_risk_officer import CrossAssetRiskOfficer
from agents.skeptic import SkepticAgent
from tools.calc.probability_simulator import EconometricProbabilitySimulator


class MeridianMultiAssetOrchestrator:
    """
    Meridian Multi-Asset Master Orchestrator:
    Coordinates specialized desks, the Cross-Asset Risk Officer, and the Skeptic Agent
    to provide institutional multi-asset research, mathematical risk modeling,
    strategy deal committee reviews, and capital allocation dossiers.
    """

    def __init__(self, ledger: Optional[ProvenanceLedger] = None, run_id: Optional[str] = None):
        rid = run_id or f"meridian_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.ledger = ledger or ProvenanceLedger(run_id=rid)
        
        # Instantiate desks and committee agents
        self.options_desk = OptionsGreekStrategist(ledger=self.ledger)
        self.futures_desk = FuturesCommodityAgent(ledger=self.ledger)
        self.macro_desk = FixedIncomeMacroAgent(ledger=self.ledger)
        self.crypto_desk = CryptoDerivativesAgent(ledger=self.ledger)
        self.risk_officer = CrossAssetRiskOfficer(ledger=self.ledger)
        self.skeptic = SkepticAgent(ledger=self.ledger)
        self.sim_engine = EconometricProbabilitySimulator()

    def run_multi_asset_committee(
        self,
        portfolio_name: str,
        total_capital_usd: float,
        allocations_usd: Dict[str, float],
        options_spec: Optional[Dict[str, Any]] = None,
        futures_spec: Optional[Dict[str, Any]] = None,
        macro_spec: Optional[Dict[str, Any]] = None,
        crypto_spec: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute full multi-asset committee review:
        1. Query Options Greek Strategist
        2. Query Futures & Commodity Desk Agent
        3. Query Fixed Income Macro Agent
        4. Query Crypto & 24/7 Derivatives Agent
        5. Submit aggregated portfolio to Cross-Asset Risk Officer
        6. Compile audited memorandum with Red Flags and HMAC-SHA256 signatures
        """
        timestamp = datetime.datetime.now().isoformat()
        desk_reports: Dict[str, Any] = {}

        # 1. Options Desk Analysis
        if options_spec:
            opt_mode = options_spec.get("mode", "contract")
            if opt_mode == "strategy":
                desk_reports["Options Greek Strategist"] = self.options_desk.evaluate_strategy(
                    strategy_name=options_spec.get("strategy_name", "Delta Hedge"),
                    underlying_ticker=options_spec.get("ticker", "SPY"),
                    spot_price=options_spec.get("spot", 500.0),
                    legs=options_spec.get("legs", []),
                    risk_free_rate=options_spec.get("risk_free_rate", 0.045)
                )
            else:
                desk_reports["Options Greek Strategist"] = self.options_desk.analyze_contract(
                    underlying_ticker=options_spec.get("ticker", "NVDA"),
                    spot_price=options_spec.get("spot", 125.0),
                    strike_price=options_spec.get("strike", 130.0),
                    time_to_expiry_years=options_spec.get("expiry_years", 45 / 365.0),
                    volatility=options_spec.get("volatility", 0.35),
                    option_type=options_spec.get("option_type", "call"),
                    market_premium=options_spec.get("premium", None)
                )
        else:
            # Default institutional options assessment
            desk_reports["Options Greek Strategist"] = self.options_desk.analyze_contract(
                underlying_ticker="SPY",
                spot_price=510.0,
                strike_price=515.0,
                time_to_expiry_years=30 / 365.0,
                volatility=0.16,
                option_type="put"
            )

        # 2. Futures Desk Analysis
        if futures_spec:
            f_mode = futures_spec.get("mode", "term_structure")
            if f_mode == "margin":
                desk_reports["Futures & Commodity Desk"] = self.futures_desk.assess_margin_and_leverage(
                    symbol=futures_spec.get("symbol", "CL"),
                    futures_price=futures_spec.get("price", 75.0),
                    contract_multiplier=futures_spec.get("multiplier", 1000.0),
                    num_contracts=futures_spec.get("contracts", 10),
                    initial_margin_per_contract=futures_spec.get("initial_margin", 6500.0),
                    maintenance_margin_per_contract=futures_spec.get("maintenance_margin", 5000.0),
                    account_equity=futures_spec.get("account_equity", 150000.0),
                    position_side=futures_spec.get("position_side", "long")
                )
            else:
                curve = futures_spec.get("curve", [
                    {"contract": "M1 (Prompt)", "days_to_expiry": 25, "price": 75.20},
                    {"contract": "M2 (+1 Mo)", "days_to_expiry": 55, "price": 76.10},
                    {"contract": "M3 (+2 Mo)", "days_to_expiry": 85, "price": 77.05},
                    {"contract": "M6 (+5 Mo)", "days_to_expiry": 175, "price": 79.40}
                ])
                desk_reports["Futures & Commodity Desk"] = self.futures_desk.evaluate_term_structure(
                    symbol=futures_spec.get("symbol", "CL"),
                    commodity_name=futures_spec.get("commodity", "WTI Crude Oil"),
                    curve=curve
                )
        else:
            # Default benchmark WTI term structure
            desk_reports["Futures & Commodity Desk"] = self.futures_desk.evaluate_term_structure(
                symbol="CL",
                commodity_name="WTI Crude Oil",
                curve=[
                    {"contract": "CL1", "days_to_expiry": 28, "price": 74.80},
                    {"contract": "CL2", "days_to_expiry": 58, "price": 75.60},
                    {"contract": "CL3", "days_to_expiry": 88, "price": 76.30}
                ]
            )

        # 3. Macro & Fixed Income Desk Analysis
        if macro_spec:
            rates = macro_spec.get("rates", {"3M": 4.80, "2Y": 3.95, "5Y": 3.85, "10Y": 4.15, "30Y": 4.45})
            desk_reports["Fixed Income Macro Agent"] = self.macro_desk.evaluate_yield_curve_macro(rates)
        else:
            desk_reports["Fixed Income Macro Agent"] = self.macro_desk.evaluate_yield_curve_macro({
                "3M": 4.90, "2Y": 4.10, "5Y": 3.90, "10Y": 4.20, "30Y": 4.50
            })

        # 4. Crypto & 24/7 Desk Analysis
        if crypto_spec:
            desk_reports["Crypto & 24/7 Derivatives Agent"] = self.crypto_desk.analyze_perpetual_funding(
                symbol=crypto_spec.get("symbol", "BTC-PERP"),
                spot_price=crypto_spec.get("spot", 64000.0),
                mark_price=crypto_spec.get("mark", 64080.0),
                funding_rate_8h_pct=crypto_spec.get("funding_8h", 0.015),
                open_interest_usd=crypto_spec.get("oi", 1_800_000_000.0),
                daily_volume_usd=crypto_spec.get("volume", 5_200_000_000.0)
            )
        else:
            desk_reports["Crypto & 24/7 Derivatives Agent"] = self.crypto_desk.analyze_perpetual_funding(
                symbol="BTC-PERP",
                spot_price=65000.0,
                mark_price=65050.0,
                funding_rate_8h_pct=0.012,
                open_interest_usd=1_500_000_000.0,
                daily_volume_usd=6_000_000_000.0
            )

        # 5. Cross-Asset Risk Officer Review
        var_analysis = self.risk_officer.evaluate_portfolio_var(
            portfolio_value_usd=total_capital_usd,
            allocations_usd=allocations_usd
        )
        stress_analysis = self.risk_officer.stress_test_portfolio(
            allocations_usd=allocations_usd
        )
        consolidated_risk = self.risk_officer.consolidate_risk_audit(
            portfolio_summary={"red_flags": var_analysis["red_flags"] + stress_analysis["red_flags"]},
            desk_reports=desk_reports
        )

        desk_reports["Cross-Asset Risk Officer"] = {
            "var_analysis": var_analysis,
            "stress_analysis": stress_analysis,
            "audit_summary": consolidated_risk,
            "red_flags": consolidated_risk["red_flags_register"]
        }

        # Master Orchestrator Provenance Registration
        master_ledger_id = self.ledger.record(
            tool="MeridianMultiAssetOrchestrator.run_multi_asset_committee",
            inputs={"portfolio": portfolio_name, "capital": total_capital_usd, "allocations": allocations_usd},
            output={"verdict": consolidated_risk["verdict"], "red_flags": consolidated_risk["total_red_flags"]},
            source="Meridian Master Orchestration Engine",
            notes=f"Portfolio '{portfolio_name}', Verdict: {consolidated_risk['verdict']}. Total red flags: {consolidated_risk['total_red_flags']}"
        )

        return {
            "orchestrator": "MERIDIAN MULTI-ASSET MASTER ORCHESTRATOR",
            "portfolio_name": portfolio_name,
            "execution_timestamp": timestamp,
            "master_ledger_id": master_ledger_id,
            "total_capital_usd": total_capital_usd,
            "allocations_usd": allocations_usd,
            "risk_verdict": consolidated_risk["verdict"],
            "verdict_rationale": consolidated_risk["verdict_rationale"],
            "total_red_flags": consolidated_risk["total_red_flags"],
            "critical_flags_count": consolidated_risk["critical_flags_count"],
            "high_flags_count": consolidated_risk["high_flags_count"],
            "medium_flags_count": consolidated_risk["medium_flags_count"],
            "red_flags_register": consolidated_risk["red_flags_register"],
            "desk_reports": desk_reports,
            "var_metrics": var_metrics_extracted(var_analysis),
            "stress_matrix": stress_analysis["stress_results"]["scenarios"]
        }

    def evaluate_strategy_deal_committee(
        self,
        symbol: str,
        strategy_name: str,
        spot_price: float,
        legs: Optional[List[Dict[str, Any]]] = None,
        target_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        horizon_days: int = 30,
        risk_free_rate: float = 0.045,
        custom_volatility: Optional[float] = None,
        custom_drift: Optional[float] = None,
        custom_skewness: Optional[float] = None,
        custom_kurtosis: Optional[float] = None,
        target_days: int = 0,
        iv_shift_pct: float = 0.0
    ) -> Dict[str, Any]:
        """
        Executes an autonomous Investment Committee Review on a specific evaluated strategy or position.
        Convenes:
        1. Options Greek Strategist (payoff, Greeks, delta/gamma/theta risks)
        2. Cross-Asset Risk Officer (Cornish-Fisher fat tails, VaR, Jarque-Bera normality)
        3. Skeptic Adversarial Agent (vol crush, liquidity, negative expectancy challenge)
        Synthesizes a consensus verdict with cryptographic HMAC-SHA256 provenance.
        """
        timestamp = datetime.datetime.now().isoformat()
        is_options = bool(legs and len(legs) > 0)

        # 1. Options Strategist Review
        if is_options:
            opt_report = self.options_desk.evaluate_strategy(
                strategy_name=strategy_name,
                underlying_ticker=symbol,
                spot_price=spot_price,
                legs=legs,
                risk_free_rate=risk_free_rate,
                target_days=target_days,
                iv_shift_pct=iv_shift_pct,
                custom_skewness=custom_skewness,
                custom_kurtosis=custom_kurtosis,
                custom_drift=custom_drift
            )
            prob_metrics = opt_report.get("probability_simulation", {}).get("probability_metrics", {})
            econo_metrics = opt_report.get("econometric_metrics", {})
            greeks_summary = opt_report.get("strategy_analysis", {})
            strat_flags = opt_report.get("red_flags", [])
        else:
            tp = target_price if target_price is not None else round(spot_price * 1.15, 2)
            sl = stop_loss_price if stop_loss_price is not None else round(spot_price * 0.90, 2)
            vol = custom_volatility if custom_volatility is not None else 0.28
            drift = custom_drift if custom_drift is not None else 0.08
            skew = custom_skewness if custom_skewness is not None else -0.40
            kurt = custom_kurtosis if custom_kurtosis is not None else 1.80

            eq_sim = self.sim_engine.simulate_equity_probability(
                spot=spot_price,
                target_price=tp,
                stop_loss_price=sl,
                horizon_days=horizon_days,
                volatility=vol,
                drift=drift,
                skewness=skew,
                kurtosis=kurt
            )
            opt_report = {
                "agent": "Equities Single Stock Specialist",
                "strategy_name": strategy_name,
                "ticker": symbol,
                "equity_simulation": eq_sim
            }
            prob_metrics = {
                "probability_of_profit_pct": eq_sim["prob_close_above_target_pct"],
                "econometric_adjusted_pop_pct": eq_sim["econometric_prob_above_target_pct"],
                "expected_value_usd": round((tp - spot_price) * (eq_sim["prob_touch_target_pct"] / 100.0) - (spot_price - sl) * (eq_sim["prob_touch_stop_loss_pct"] / 100.0), 2),
                "win_loss_ratio": eq_sim["risk_reward_ratio"],
                "kelly_fraction_half_pct": 12.5
            }
            econo_metrics = eq_sim["econometric_metrics"]
            greeks_summary = {"net_delta": 1.0, "net_gamma": 0.0, "net_vega": 0.0, "net_theta_daily": 0.0}
            strat_flags = []

        # 2. Cross-Asset Risk Officer Review
        cro_report = self.risk_officer.evaluate_asset_tail_risk(
            ticker=symbol,
            spot_price=spot_price,
            horizon_days=horizon_days,
            custom_volatility=custom_volatility
        )
        cro_flags = cro_report.get("red_flags", [])

        # 3. Skeptic Adversarial Agent Review
        skeptic_report = self.skeptic.audit_derivatives_strategy_thesis(
            ticker=symbol,
            strategy_name=strategy_name,
            spot_price=spot_price,
            probability_metrics=prob_metrics,
            econometric_metrics=econo_metrics,
            greeks_summary=greeks_summary
        )

        # 4. Master Consensus Synthesis
        all_committee_flags = []
        for f in strat_flags:
            cf = dict(f)
            cf["source"] = "Options Greek Strategist"
            all_committee_flags.append(cf)

        for f in cro_flags:
            cf = dict(f)
            cf["source"] = "Cross-Asset Risk Officer"
            all_committee_flags.append(cf)

        for c in skeptic_report.get("adversarial_challenges", []):
            all_committee_flags.append({
                "severity": c.get("severity", "MEDIUM"),
                "category": f"Skeptic: {c.get('challenge')}",
                "message": c.get("argument"),
                "source": "Skeptic Agent"
            })

        crit_count = sum(1 for f in all_committee_flags if f.get("severity") == "CRITICAL")
        high_count = sum(1 for f in all_committee_flags if f.get("severity") == "HIGH")
        med_count = sum(1 for f in all_committee_flags if f.get("severity") == "MEDIUM")

        pop = prob_metrics.get("probability_of_profit_pct", 50.0)
        ev = prob_metrics.get("expected_value_usd", 0.0)
        skeptic_score = skeptic_report.get("skeptic_score", 70.0)

        # Quantitative Confidence Score (0 to 100)
        base_score = (pop * 0.4) + (skeptic_score * 0.3)
        if ev > 0:
            base_score += min(20.0, (ev / spot_price) * 100.0)
        else:
            base_score -= 25.0

        base_score -= (crit_count * 30.0) + (high_count * 10.0) + (med_count * 4.0)
        confidence_score = float(max(5.0, min(95.0, base_score)))

        if crit_count > 0 or ev < 0 or confidence_score < 45.0:
            verdict = "REJECTED"
            rationale = "Strategy carries unacceptable negative expected value, catastrophic uncapped tail risk, or severe adversarial objections."
        elif high_count > 0 or confidence_score < 68.0:
            verdict = "CONDITIONAL_APPROVAL"
            rationale = "Strategy is mathematically viable, but elevated tail risk surcharge or delta drift requires strict sizing caps and stop-loss enforcement."
        else:
            verdict = "APPROVED"
            rationale = "Strategy satisfies institutional quantitative hurdles: positive EV, robust fat-tail POP, and favorable Kelly capital sizing."

        # Actionable Mitigations
        mitigations = []
        if prob_metrics.get("kelly_fraction_half_pct", 0.0) > 0:
            mitigations.append(f"Cap allocation to Half-Kelly recommendation ({prob_metrics['kelly_fraction_half_pct']:.1f}% of capital).")
        if econo_metrics.get("var_metrics", {}).get("fat_tail_surcharge_95_pct", 0) > 2.0:
            cf_cone_low = econo_metrics.get("standard_deviation_cones", {}).get("econometric_adjusted", {}).get("minus_2_sigma_cf")
            if cf_cone_low:
                mitigations.append(f"Establish trailing protective stop at Cornish-Fisher -2σ level (${cf_cone_low:,.2f}).")
        if high_count > 0:
            mitigations.append("Avoid holding through major earnings or Fed rate decision dates without wing put hedges.")

        # Ledger Registration
        ledger_id = self.ledger.record(
            tool="MeridianMultiAssetOrchestrator.evaluate_strategy_deal_committee",
            inputs={"ticker": symbol, "strategy": strategy_name, "spot": spot_price, "pop": pop, "ev": ev},
            output={"verdict": verdict, "confidence_score": confidence_score, "flags": len(all_committee_flags)},
            source="Meridian Master Investment Committee",
            ticker=symbol,
            notes=f"Deal Committee for {symbol} {strategy_name}: Verdict {verdict} ({confidence_score:.0f}/100)"
        )

        return {
            "orchestrator": "MERIDIAN MULTI-ASSET MASTER ORCHESTRATOR",
            "symbol": symbol,
            "strategy_name": strategy_name,
            "timestamp": timestamp,
            "verdict": verdict,
            "confidence_score": round(confidence_score, 1),
            "verdict_rationale": rationale,
            "provenance_ledger_id": ledger_id,
            "desk_reports": {
                "Options Greek Strategist": opt_report,
                "Cross-Asset Risk Officer": cro_report,
                "Skeptic Agent": skeptic_report
            },
            "red_flags": all_committee_flags,
            "mitigations": mitigations,
            "probability_metrics": prob_metrics,
            "econometric_metrics": econo_metrics
        }


def var_metrics_extracted(var_analysis: Dict[str, Any]) -> Dict[str, Any]:
    vm = var_analysis.get("var_metrics", {})
    return {
        "var_95_pct": vm.get("var_95_pct"),
        "var_95_dollar": vm.get("var_95_dollar"),
        "var_99_pct": vm.get("var_99_pct"),
        "var_99_dollar": vm.get("var_99_dollar"),
        "cvar_99_pct": vm.get("cvar_99_pct"),
        "cvar_99_dollar": vm.get("cvar_99_dollar"),
        "annualized_vol_pct": vm.get("annualized_portfolio_volatility_pct")
    }
