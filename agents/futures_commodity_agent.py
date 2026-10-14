"""
agents/futures_commodity_agent.py
Futures & Commodity Desk Agent
Specialized quantitative desk agent for physical & financial futures:
- Cost-of-carry pricing models across Energy, Metals, Agriculture, and Index futures
- Term structure curvature: Contango vs. Backwardation dynamics
- Annualized roll yield decay / boost tracking
- Exchange initial & maintenance margin modeling, leverage buffers, and liquidation alerts
"""

import datetime
from typing import Dict, Any, List, Optional
from tools.ledger import ProvenanceLedger
from tools.calc.derivatives_math import FuturesCommodityEngine


class FuturesCommodityAgent:
    """
    Futures & Commodity Desk Agent: Evaluates futures curves, models roll yields,
    and stress-tests exchange leverage and margin headroom.
    """

    def __init__(self, ledger: Optional[ProvenanceLedger] = None):
        self.ledger = ledger or ProvenanceLedger(run_id=f"futures_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.agent_role = "Futures & Commodity Desk Agent"

    def analyze_commodity_contract(
        self,
        symbol: str,
        commodity_name: str,
        spot_price: float,
        time_to_expiry_years: float,
        risk_free_rate: float = 0.045,
        storage_cost_annual: float = 0.02,
        convenience_yield_annual: float = 0.01
    ) -> Dict[str, Any]:
        """
        Evaluate theoretical cost-of-carry price, basis, and market regime for a commodity contract.
        """
        model_res = FuturesCommodityEngine.theoretical_futures_price(
            spot=spot_price,
            time_to_expiry_years=time_to_expiry_years,
            risk_free_rate=risk_free_rate,
            storage_cost_annual=storage_cost_annual,
            convenience_yield_annual=convenience_yield_annual
        )

        ledger_id = self.ledger.record(
            tool="FuturesCommodityEngine.theoretical_futures_price",
            inputs={
                "symbol": symbol,
                "commodity": commodity_name,
                "spot": spot_price,
                "expiry_years": time_to_expiry_years,
                "r": risk_free_rate,
                "storage": storage_cost_annual,
                "convenience_yield": convenience_yield_annual
            },
            output=model_res,
            source="Cost-of-Carry Futures Pricing Model",
            ticker=symbol,
            notes=f"{commodity_name} theoretical future ${model_res['theoretical_futures_price']}, regime {model_res['regime']}"
        )

        red_flags = []
        if model_res["net_cost_of_carry_annual_pct"] > 8.0:
            red_flags.append({
                "severity": "MEDIUM",
                "category": "High Carrying Cost Drag",
                "message": f"Annualized net carrying cost ({model_res['net_cost_of_carry_annual_pct']}%) creates heavy structural headwinds for long holders."
            })

        return {
            "agent": self.agent_role,
            "symbol": symbol,
            "commodity_name": commodity_name,
            "pricing": model_res,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags
        }

    def evaluate_term_structure(
        self,
        symbol: str,
        commodity_name: str,
        curve: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze term structure curvature across contract expirations to compute roll yields.
        """
        curve_res = FuturesCommodityEngine.analyze_term_structure(curve)

        ledger_id = self.ledger.record(
            tool="FuturesCommodityEngine.analyze_term_structure",
            inputs={"symbol": symbol, "commodity": commodity_name, "contracts": len(curve)},
            output={"regime": curve_res["curve_regime"], "roll_yield": curve_res["front_to_deferred_roll_yield_annual_pct"]},
            source="Futures Term Structure Curve Engine",
            ticker=symbol,
            notes=f"{commodity_name} curve: {curve_res['curve_regime']}, roll yield {curve_res['front_to_deferred_roll_yield_annual_pct']}%"
        )

        red_flags = []
        # Severe contango roll decay
        if curve_res["is_contango"] and curve_res["front_to_deferred_roll_yield_annual_pct"] < -10.0:
            red_flags.append({
                "severity": "HIGH",
                "category": "Severe Contango Roll Decay",
                "message": f"Steep contango structure creates a {abs(curve_res['front_to_deferred_roll_yield_annual_pct']):.1f}% annualized negative roll decay on passive long positions."
            })
        elif not curve_res["is_contango"] and curve_res["front_to_deferred_roll_yield_annual_pct"] > 15.0:
            # Positive backwardation tailwind
            pass

        return {
            "agent": self.agent_role,
            "symbol": symbol,
            "commodity_name": commodity_name,
            "term_structure": curve_res,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags,
            "tactical_bias": "SHORT_ROLL_HARVEST" if curve_res["is_contango"] else "LONG_BACKWARDATION_ACCUMULATE"
        }

    def assess_margin_and_leverage(
        self,
        symbol: str,
        futures_price: float,
        contract_multiplier: float,
        num_contracts: int,
        initial_margin_per_contract: float,
        maintenance_margin_per_contract: float,
        account_equity: float,
        position_side: str = "long"
    ) -> Dict[str, Any]:
        """
        Stress test position margin utilization, effective leverage, and margin call thresholds.
        """
        margin_res = FuturesCommodityEngine.calculate_margin_buffer(
            contract_multiplier=contract_multiplier,
            futures_price=futures_price,
            num_contracts=num_contracts,
            initial_margin_per_contract=initial_margin_per_contract,
            maintenance_margin_per_contract=maintenance_margin_per_contract,
            account_equity=account_equity,
            position_side=position_side
        )

        ledger_id = self.ledger.record(
            tool="FuturesCommodityEngine.calculate_margin_buffer",
            inputs={"symbol": symbol, "contracts": num_contracts, "equity": account_equity, "side": position_side},
            output={"leverage": margin_res["effective_leverage"], "utilization": margin_res["margin_utilization_pct"]},
            source="Exchange Margin Risk Engine",
            ticker=symbol,
            notes=f"Effective leverage {margin_res['effective_leverage']}x, Margin utilization {margin_res['margin_utilization_pct']}%"
        )

        red_flags = []
        if margin_res["effective_leverage"] > 10.0:
            red_flags.append({
                "severity": "CRITICAL",
                "category": "Hyper-Leverage Exposure",
                "message": f"Position leverage of {margin_res['effective_leverage']:.1f}x exceeds institutional safety cap (10.0x)."
            })
        if margin_res["margin_utilization_pct"] > 80.0:
            red_flags.append({
                "severity": "CRITICAL",
                "category": "Margin Depletion Imminent",
                "message": f"Margin utilization is {margin_res['margin_utilization_pct']:.1f}%. Immediate capital injection or position downsizing required."
            })
        elif margin_res["margin_utilization_pct"] > 60.0:
            red_flags.append({
                "severity": "HIGH",
                "category": "Elevated Margin Utilization",
                "message": f"Margin utilization at {margin_res['margin_utilization_pct']:.1f}% leaves insufficient cushion for market volatility spikes."
            })
        if margin_res["max_adverse_move_pct"] < 5.0:
            red_flags.append({
                "severity": "CRITICAL",
                "category": "Tight Margin Call Haircut",
                "message": f"A mere {margin_res['max_adverse_move_pct']:.1f}% adverse price move triggers a forced maintenance margin call."
            })

        return {
            "agent": self.agent_role,
            "symbol": symbol,
            "margin_audit": margin_res,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags,
            "verdict": "APPROVED" if not any(rf["severity"] == "CRITICAL" for rf in red_flags) else "REJECTED"
        }
