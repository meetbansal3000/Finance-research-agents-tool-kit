"""
agents/options_greek_agent.py
Options Greek Strategist Agent
Specialized quantitative agent for equity and index derivatives:
- Volatility surface & smile/skew analysis
- First-order & second-order Black-Scholes Greeks (Delta, Gamma, Vega, Theta, Rho, Vanna, Volga, Charm)
- Multi-leg strategy modeling (Straddles, Spreads, Iron Condors, Collars)
- Hedging advice & options risk flags (pin risk, gamma squeeze, tail hedging)
"""

import datetime
from typing import Dict, Any, List, Optional
from tools.ledger import ProvenanceLedger
from tools.calc.derivatives_math import BlackScholesEngine


class OptionsGreekStrategist:
    """
    Options Greek Strategist: Evaluates derivative contracts, models volatility skew,
    computes exact mathematical Greeks, and identifies options vulnerabilities.
    """

    def __init__(self, ledger: Optional[ProvenanceLedger] = None):
        self.ledger = ledger or ProvenanceLedger(run_id=f"options_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.agent_role = "Options Greek Strategist"

    def analyze_contract(
        self,
        underlying_ticker: str,
        spot_price: float,
        strike_price: float,
        time_to_expiry_years: float,
        volatility: float,
        risk_free_rate: float = 0.045,
        dividend_yield: float = 0.0,
        option_type: str = "call",
        market_premium: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single option contract with full Greek sensitivities and ledger provenance.
        """
        greeks = BlackScholesEngine.price_and_greeks(
            spot=spot_price,
            strike=strike_price,
            time_to_expiry=time_to_expiry_years,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            dividend_yield=dividend_yield,
            option_type=option_type
        )

        implied_vol = volatility
        if market_premium is not None and market_premium > 0:
            implied_vol = BlackScholesEngine.implied_volatility(
                market_price=market_premium,
                spot=spot_price,
                strike=strike_price,
                time_to_expiry=time_to_expiry_years,
                risk_free_rate=risk_free_rate,
                dividend_yield=dividend_yield,
                option_type=option_type
            )

        # Provenance ledger registration
        ledger_id = self.ledger.record(
            tool="BlackScholesEngine.price_and_greeks",
            inputs={
                "ticker": underlying_ticker,
                "spot": spot_price,
                "strike": strike_price,
                "expiry_years": time_to_expiry_years,
                "volatility": volatility,
                "type": option_type
            },
            output=greeks,
            source="Black-Scholes-Merton Analytical Model",
            ticker=underlying_ticker,
            notes=f"Fair value ${greeks['price']}, Delta {greeks['delta']}, Gamma {greeks['gamma']}"
        )

        # Red flags detection
        red_flags = []
        moneyness = spot_price / strike_price
        if abs(greeks["gamma"]) > 0.05 and time_to_expiry_years < (7.0 / 365.0):
            red_flags.append({
                "severity": "HIGH",
                "category": "Gamma Cliff Risk",
                "message": f"Contract is within 7 days of expiry with elevated Gamma ({greeks['gamma']}). High acceleration hazard."
            })
        if option_type.lower() == "call" and moneyness > 1.25 and greeks["delta"] > 0.90:
            red_flags.append({
                "severity": "MEDIUM",
                "category": "Deep ITM Capital Inefficiency",
                "message": f"Call is deep ITM (Delta {greeks['delta']}). Acts almost identically to underlying stock without leverage advantage."
            })
        if time_to_expiry_years < (14.0 / 365.0) and abs(greeks["theta_daily"]) > 0.02 * greeks["price"]:
            red_flags.append({
                "severity": "HIGH",
                "category": "Theta Burn Acceleration",
                "message": f"Severe time decay: daily theta burn (${abs(greeks['theta_daily']):.2f}) is exceeding 2% of option value per day."
            })

        return {
            "agent": self.agent_role,
            "ticker": underlying_ticker,
            "contract": f"{underlying_ticker} ${strike_price} {option_type.upper()} ({time_to_expiry_years*365:.0f} DTE)",
            "greeks": greeks,
            "implied_volatility": round(float(implied_vol), 4),
            "moneyness": round(float(moneyness), 4),
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags,
            "hedging_delta_shares_per_contract": round(float(greeks["delta"] * 100.0), 1)
        }

    def evaluate_strategy(
        self,
        strategy_name: str,
        underlying_ticker: str,
        spot_price: float,
        legs: List[Dict[str, Any]],
        risk_free_rate: float = 0.045
    ) -> Dict[str, Any]:
        """
        Evaluate a complete multi-leg option strategy (e.g. Iron Condor, Straddle, Collar).
        """
        result = BlackScholesEngine.analyze_strategy_legs(
            spot=spot_price,
            legs=legs,
            risk_free_rate=risk_free_rate
        )

        ledger_id = self.ledger.record(
            tool="BlackScholesEngine.analyze_strategy_legs",
            inputs={"ticker": underlying_ticker, "strategy": strategy_name, "spot": spot_price, "legs": len(legs)},
            output={"net_delta": result["net_delta"], "net_vega": result["net_vega"], "cost": result["net_debit_credit"]},
            source="Options Strategy Risk Engine",
            ticker=underlying_ticker,
            notes=f"Strategy: {strategy_name}, Delta {result['net_delta']}, Max Loss {result['max_loss']}"
        )

        red_flags = []
        if result["max_loss"] == "Unlimited" or (isinstance(result["max_loss"], (int, float)) and result["max_loss"] < -5000):
            red_flags.append({
                "severity": "CRITICAL",
                "category": "Uncapped Tail Risk",
                "message": f"Strategy carries catastrophic undefined tail risk ({result['max_loss']}). Mandatory stop-loss or wing hedge required."
            })
        if abs(result["net_delta"]) > 0.50 and "neutral" in strategy_name.lower():
            red_flags.append({
                "severity": "HIGH",
                "category": "Delta Drift Imbalance",
                "message": f"Supposedly market-neutral strategy exhibits directional Delta bias ({result['net_delta']}). Rebalancing needed."
            })
        if result["net_gamma"] < -0.01:
            red_flags.append({
                "severity": "HIGH",
                "category": "Short Gamma Vulnerability",
                "message": "Negative net Gamma. Vulnerable to sudden volatility spikes or gap openings."
            })

        return {
            "agent": self.agent_role,
            "strategy_name": strategy_name,
            "ticker": underlying_ticker,
            "strategy_analysis": result,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags,
            "verdict": "APPROVED" if not any(rf["severity"] == "CRITICAL" for rf in red_flags) else "REJECTED"
        }
