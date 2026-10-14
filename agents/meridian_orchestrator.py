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


class MeridianMultiAssetOrchestrator:
    """
    Meridian Multi-Asset Master Orchestrator:
    Coordinates 5 specialized desks to provide institutional multi-asset research,
    mathematical risk modeling, and capital allocation dossiers.
    """

    def __init__(self, ledger: Optional[ProvenanceLedger] = None, run_id: Optional[str] = None):
        rid = run_id or f"meridian_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.ledger = ledger or ProvenanceLedger(run_id=rid)
        
        # Instantiate 5 specialized desks
        self.options_desk = OptionsGreekStrategist(ledger=self.ledger)
        self.futures_desk = FuturesCommodityAgent(ledger=self.ledger)
        self.macro_desk = FixedIncomeMacroAgent(ledger=self.ledger)
        self.crypto_desk = CryptoDerivativesAgent(ledger=self.ledger)
        self.risk_officer = CrossAssetRiskOfficer(ledger=self.ledger)

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
