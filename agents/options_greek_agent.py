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
from tools.calc.probability_simulator import EconometricProbabilitySimulator


class OptionsGreekStrategist:
    """
    Options Greek Strategist: Evaluates derivative contracts, models volatility skew,
    computes exact mathematical Greeks, runs econometric probability simulations,
    and identifies options vulnerabilities.
    """

    def __init__(self, ledger: Optional[ProvenanceLedger] = None):
        self.ledger = ledger or ProvenanceLedger(run_id=f"options_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.agent_role = "Options Greek Strategist"
        self.sim_engine = EconometricProbabilitySimulator()

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
        if (abs(greeks["gamma"]) > 0.02 or (spot_price * abs(greeks["gamma"])) > 1.0) and time_to_expiry_years < (7.0 / 365.0):
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
        risk_free_rate: float = 0.045,
        target_days: int = 0,
        iv_shift_pct: float = 0.0,
        custom_skewness: Optional[float] = None,
        custom_kurtosis: Optional[float] = None,
        custom_drift: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a complete multi-leg option strategy (e.g. Iron Condor, Straddle, Collar)
        with Black-Scholes Greeks, full econometric probability simulation,
        Cornish-Fisher fat-tail adjustments, Kelly sizing, and red-flag gatekeeping.
        """
        result = BlackScholesEngine.analyze_strategy_legs(
            spot=spot_price,
            legs=legs,
            risk_free_rate=risk_free_rate
        )

        # 1. Empirical moments & econometric probability simulation
        moments = self.sim_engine.calculate_empirical_moments(underlying_ticker)
        skew = custom_skewness if custom_skewness is not None else float(moments["sample_skewness"])
        kurt = custom_kurtosis if custom_kurtosis is not None else float(moments["sample_excess_kurtosis"])
        drift = custom_drift if custom_drift is not None else float(moments["annualized_drift"])

        prob_sim = self.sim_engine.simulate_options_strategy_probability(
            spot=spot_price,
            legs=legs,
            risk_free_rate=risk_free_rate,
            custom_drift=drift,
            skewness=skew,
            kurtosis=kurt,
            target_days=target_days,
            iv_shift_pct=iv_shift_pct
        )

        pm = prob_sim["probability_metrics"]
        econo = prob_sim["econometric_metrics"]

        ledger_id = self.ledger.record(
            tool="EconometricProbabilitySimulator.simulate_options_strategy_probability",
            inputs={"ticker": underlying_ticker, "strategy": strategy_name, "spot": spot_price, "legs": len(legs), "skew": skew, "kurt": kurt},
            output={
                "net_delta": result["net_delta"],
                "pop_pct": pm["probability_of_profit_pct"],
                "pop_adj_pct": pm["econometric_adjusted_pop_pct"],
                "expected_value_usd": pm["expected_value_usd"],
                "kelly_half_pct": pm["kelly_fraction_half_pct"]
            },
            source="Options Strategy & Econometric Probability Engine",
            ticker=underlying_ticker,
            notes=f"Strategy: {strategy_name}, POP {pm['probability_of_profit_pct']}%, EV ${pm['expected_value_usd']}, Kelly {pm['kelly_fraction_half_pct']}%"
        )

        red_flags = []
        if result["max_loss"] == "Unlimited" or (isinstance(result["max_loss"], (int, float)) and result["max_loss"] < -5 * 1000):
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

        # Econometric Probability & Tail-Risk Red Flags
        if pm["expected_value_usd"] < 0:
            red_flags.append({
                "severity": "HIGH",
                "category": "Negative Statistical Expectancy",
                "message": f"Statistical expected value is negative (${pm['expected_value_usd']:+,.2f} USD). Expected return does not justify risk."
            })
        if (pm["probability_of_profit_pct"] - pm["econometric_adjusted_pop_pct"]) > 4.0:
            red_flags.append({
                "severity": "HIGH",
                "category": "Fat-Tail POP Decay",
                "message": f"Gaussian POP ({pm['probability_of_profit_pct']:.1f}%) significantly overstates profit probability by {pm['probability_of_profit_pct'] - pm['econometric_adjusted_pop_pct']:.1f}% under empirical fat-tail leptokurtosis."
            })
        if econo["var_metrics"]["fat_tail_surcharge_95_pct"] > 3.0:
            red_flags.append({
                "severity": "MEDIUM",
                "category": "Fat-Tail VaR Surcharge",
                "message": f"95% Downside VaR incurs a +{econo['var_metrics']['fat_tail_surcharge_95_pct']:.2f}% (+${econo['var_metrics']['fat_tail_surcharge_95_dollars']:,.2f} USD) surcharge due to empirical negative skewness and leptokurtosis."
            })

        return {
            "agent": self.agent_role,
            "strategy_name": strategy_name,
            "ticker": underlying_ticker,
            "strategy_analysis": result,
            "probability_simulation": prob_sim,
            "empirical_moments": moments,
            "econometric_metrics": econo,
            "provenance_ledger_id": ledger_id,
            "red_flags": red_flags,
            "verdict": "APPROVED" if not any(rf["severity"] == "CRITICAL" for rf in red_flags) else "REJECTED"
        }
