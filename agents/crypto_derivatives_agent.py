"""
agents/crypto_derivatives_agent.py
Crypto & 24/7 Derivatives Agent
Specialized quantitative desk agent for continuous digital asset derivatives:
- Perpetual swap 8h funding rate analytics & APY annualization
- Cash-and-carry basis arbitrage (spot vs dated quarterly futures)
- Liquidation cascade risk modeling & margin buffer distances
- 24/7 market microstructure, orderbook depth & volatility skew
"""

import datetime
from typing import Dict, Any, List, Optional
from tools.ledger import ProvenanceLedger
from tools.calc.derivatives_math import CryptoDerivativesEngine


class CryptoDerivativesAgent:
    """
    Crypto & 24/7 Derivatives Agent: Monitors continuous funding rates,
    basis spreads, and exchange liquidation cascade vulnerabilities.
    """

    def __init__(self, ledger: Optional[ProvenanceLedger] = None):
        self.ledger = ledger or ProvenanceLedger(run_id=f"crypto_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.agent_role = "Crypto & 24/7 Derivatives Agent"

    def analyze_perpetual_funding(
        self,
        symbol: str,
        spot_price: float,
        mark_price: float,
        funding_rate_8h_pct: float,
        open_interest_usd: float = 1.2 * 1000000000.0,
        daily_volume_usd: float = 4.5 * 1000000000.0
    ) -> Dict[str, Any]:
        """
        Evaluate perpetual swap funding rate dynamics, annualized carry, and liquidation risk.
        """
        funding_res = CryptoDerivativesEngine.perpetual_funding_analytics(
            funding_rate_8h_pct=funding_rate_8h_pct,
            spot_price=spot_price,
            mark_price=mark_price,
            open_interest_usd=open_interest_usd,
            daily_volume_usd=daily_volume_usd
        )

        ledger_id = self.ledger.record(
            tool="CryptoDerivativesEngine.perpetual_funding_analytics",
            inputs={"symbol": symbol, "spot": spot_price, "mark": mark_price, "funding_8h": funding_rate_8h_pct},
            output={"apy": funding_res["simple_annualized_pct"], "cascade_risk": funding_res["liquidation_cascade_risk_score"]},
            source="Crypto Perpetual Microstructure Engine",
            ticker=symbol,
            notes=f"{symbol} Perp funding APY {funding_res['simple_annualized_pct']}%, Cascade Risk: {funding_res['cascade_alert']}"
        )

        red_flags = []
        if funding_res["liquidation_cascade_risk_score"] > 70.0:
            red_flags.append({
                "severity": "CRITICAL",
                "category": "Liquidation Cascade Hazard",
                "message": f"High open interest relative to daily volume ({funding_res['oi_to_volume_ratio']:.2f}) with crowded funding indicates imminent squeeze risk."
            })
        if abs(funding_res["simple_annualized_pct"]) > 40.0:
            red_flags.append({
                "severity": "HIGH",
                "category": "Extreme Crowded Funding Dislocation",
                "message": f"Funding APY of {funding_res['simple_annualized_pct']:.1f}% indicates excessive speculative leverage imbalance."
            })

        return {
            "agent": self.agent_role,
            "symbol": symbol,
            "funding_analysis": funding_res,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags,
            "arbitrage_recommendation": "HARVEST_FUNDING_DELTA_NEUTRAL" if funding_res["simple_annualized_pct"] > 15.0 else "NEUTRAL"
        }

    def evaluate_basis_arbitrage(
        self,
        symbol: str,
        spot_price: float,
        dated_futures_price: float,
        days_to_expiry: float,
        maker_taker_fee_pct: float = 0.08,
        borrow_cost_annual_pct: float = 2.0
    ) -> Dict[str, Any]:
        """
        Evaluate Cash-and-Carry Arbitrage opportunities between spot and dated futures.
        """
        basis_res = CryptoDerivativesEngine.cash_and_carry_basis(
            spot_price=spot_price,
            futures_price=dated_futures_price,
            days_to_expiry=days_to_expiry,
            maker_taker_fee_pct=maker_taker_fee_pct,
            borrow_cost_annual_pct=borrow_cost_annual_pct
        )

        ledger_id = self.ledger.record(
            tool="CryptoDerivativesEngine.cash_and_carry_basis",
            inputs={"symbol": symbol, "spot": spot_price, "futures": dated_futures_price, "days": days_to_expiry},
            output={"net_apy": basis_res["net_annualized_apy_pct"], "viable": basis_res["arbitrage_viable"]},
            source="Crypto Basis Arbitrage Engine",
            ticker=symbol,
            notes=f"{symbol} Cash & Carry Net APY {basis_res['net_annualized_apy_pct']}%"
        )

        red_flags = []
        if basis_res["net_annualized_apy_pct"] < 0:
            red_flags.append({
                "severity": "HIGH",
                "category": "Negative Basis Drag",
                "message": f"Dated futures trading at backwardation discount ({basis_res['gross_basis_pct']:.2f}%). Long futures carry yields negative net return."
            })

        return {
            "agent": self.agent_role,
            "symbol": symbol,
            "basis_arbitrage": basis_res,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags
        }

    def evaluate_liquidation_buffer(
        self,
        symbol: str,
        entry_price: float,
        leverage: float,
        position_side: str = "long",
        maintenance_margin_rate: float = 0.005
    ) -> Dict[str, Any]:
        """
        Assess position liquidation distance and 24/7 flash crash risk.
        """
        liq_res = CryptoDerivativesEngine.liquidation_price(
            entry_price=entry_price,
            leverage=leverage,
            position_side=position_side,
            maintenance_margin_rate=maintenance_margin_rate
        )

        ledger_id = self.ledger.record(
            tool="CryptoDerivativesEngine.liquidation_price",
            inputs={"symbol": symbol, "entry": entry_price, "leverage": leverage, "side": position_side},
            output={"liq_price": liq_res["liquidation_price"], "buffer": liq_res["adverse_buffer_pct"]},
            source="Crypto Liquidation Distance Engine",
            ticker=symbol,
            notes=f"Liquidation price ${liq_res['liquidation_price']} (Buffer: {liq_res['adverse_buffer_pct']}%)"
        )

        red_flags = []
        if leverage > 20.0:
            red_flags.append({
                "severity": "CRITICAL",
                "category": "Reckless 24/7 Crypto Leverage",
                "message": f"Leverage of {leverage:.0f}x in a 24/7 continuous crypto asset with high historical volatility presents catastrophic wipeout risk."
            })
        if liq_res["adverse_buffer_pct"] < 8.0:
            red_flags.append({
                "severity": "CRITICAL",
                "category": "Flash Liquidation Vulnerability",
                "message": f"Liquidation distance is only {liq_res['adverse_buffer_pct']:.1f}%. A routine intraday wick could trigger automated liquidation."
            })

        return {
            "agent": self.agent_role,
            "symbol": symbol,
            "liquidation_metrics": liq_res,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags,
            "verdict": "APPROVED" if not any(rf["severity"] == "CRITICAL" for rf in red_flags) else "REJECTED"
        }
