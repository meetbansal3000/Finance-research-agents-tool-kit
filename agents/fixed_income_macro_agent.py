"""
agents/fixed_income_macro_agent.py
Fixed Income Macro Agent
Specialized quantitative macro and fixed income agent:
- Sovereign yield curve structure (3M, 2Y, 5Y, 10Y, 30Y) & recession inversion detection
- Bond portfolio sensitivity: Macaulay Duration, Modified Duration, Convexity, and DV01
- Interest rate shock stress tests (-200 bps to +200 bps)
- Central bank policy trajectory & inflation breakeven monitoring
"""

import datetime
from typing import Dict, Any, List, Optional
from tools.ledger import ProvenanceLedger
from tools.calc.derivatives_math import FixedIncomeMacroEngine


class FixedIncomeMacroAgent:
    """
    Fixed Income Macro Agent: Analyzes interest rate curves, duration risk,
    DV01 price sensitivity, and macroeconomic monetary policy shifts.
    """

    def __init__(self, ledger: Optional[ProvenanceLedger] = None):
        self.ledger = ledger or ProvenanceLedger(run_id=f"macro_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.agent_role = "Fixed Income Macro Agent"

    def analyze_bond(
        self,
        security_name: str,
        face_value: float,
        coupon_rate_annual: float,
        yield_to_maturity_annual: float,
        years_to_maturity: float,
        payments_per_year: int = 2
    ) -> Dict[str, Any]:
        """
        Compute dirty price, duration, convexity, DV01, and rate shock sensitivity.
        """
        metrics = FixedIncomeMacroEngine.bond_sensitivities(
            face_value=face_value,
            coupon_rate_annual=coupon_rate_annual,
            yield_to_maturity_annual=yield_to_maturity_annual,
            years_to_maturity=years_to_maturity,
            payments_per_year=payments_per_year
        )

        ledger_id = self.ledger.record(
            tool="FixedIncomeMacroEngine.bond_sensitivities",
            inputs={
                "security": security_name,
                "par": face_value,
                "coupon": coupon_rate_annual,
                "ytm": yield_to_maturity_annual,
                "maturity_years": years_to_maturity
            },
            output={"duration": metrics["modified_duration"], "dv01": metrics["dv01_per_million_par"]},
            source="Institutional Bond Duration & Convexity Engine",
            ticker=security_name,
            notes=f"Modified Duration {metrics['modified_duration']}, DV01/M ${metrics['dv01_per_million_par']}"
        )

        red_flags = []
        if metrics["modified_duration"] > 12.0:
            red_flags.append({
                "severity": "HIGH",
                "category": "Ultra-Long Duration Exposure",
                "message": f"Modified duration of {metrics['modified_duration']:.1f} creates extreme capital volatility under upward rate repricing."
            })
        if metrics["convexity"] < 0:
            red_flags.append({
                "severity": "HIGH",
                "category": "Negative Convexity Hazard",
                "message": "Negative convexity profile limits price upside during rate rallies while accelerating downside losses."
            })

        return {
            "agent": self.agent_role,
            "security_name": security_name,
            "metrics": metrics,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags
        }

    def evaluate_yield_curve_macro(
        self,
        rates_curve: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Analyze Treasury yield curve inversion, steepness, and macro regime.
        """
        curve_res = FixedIncomeMacroEngine.evaluate_yield_curve(rates_curve)

        ledger_id = self.ledger.record(
            tool="FixedIncomeMacroEngine.evaluate_yield_curve",
            inputs={"rates": rates_curve},
            output={"regime": curve_res["curve_regime"], "2y10y": curve_res["spread_2y_10y_bps"]},
            source="Treasury Yield Curve Macro Engine",
            ticker="US_TREASURY_CURVE",
            notes=f"Curve: {curve_res['curve_regime']}, 2Y-10Y Spread {curve_res['spread_2y_10y_bps']} bps"
        )

        red_flags = []
        if curve_res["is_inverted"]:
            red_flags.append({
                "severity": "CRITICAL" if curve_res["spread_2y_10y_bps"] < -50 else "HIGH",
                "category": "Yield Curve Inversion Alert",
                "message": f"2Y-10Y curve is inverted by {abs(curve_res['spread_2y_10y_bps'])} bps. Historically reliable recession leading indicator."
            })
        if curve_res.get("spread_3m_10y_bps", 0) < -75:
            red_flags.append({
                "severity": "CRITICAL",
                "category": "Severe Money Market Dislocation",
                "message": f"3M-10Y spread is deeply inverted ({curve_res['spread_3m_10y_bps']} bps), reflecting aggressive short-term rate tightening."
            })

        return {
            "agent": self.agent_role,
            "yield_curve_analysis": curve_res,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags,
            "portfolio_duration_recommendation": "UNDERWEIGHT_DURATION" if curve_res["is_inverted"] else "NEUTRAL_BENCHMARK"
        }
