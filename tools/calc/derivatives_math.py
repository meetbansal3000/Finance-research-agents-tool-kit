"""
tools/calc/derivatives_math.py
Institutional Multi-Asset Quantitative Models for Meridian Terminal:
1. Black-Scholes-Merton Options Pricing & First/Second-Order Greeks Engine
2. Futures & Commodity Cost-of-Carry, Term Structure & Roll Yield Engine
3. Fixed Income Duration, Convexity, DV01 & Yield Curve Regime Engine
4. Crypto & 24/7 Perpetual Funding, Basis Arbitrage & Liquidation Engine
5. Cross-Asset Parametric/Historical VaR, CVaR & Crisis Stress-Testing Engine
"""

import math
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


# =============================================================================
# 1. OPTIONS GREEK ENGINE (Black-Scholes-Merton & Analytical Greeks)
# =============================================================================

class BlackScholesEngine:
    """
    Institutional Black-Scholes-Merton option pricing and sensitivity engine.
    Computes European Call/Put fair value, analytical first-order Greeks (Delta, Vega,
    Theta, Rho) and second-order Greeks (Gamma, Vanna, Volga, Charm).
    """

    @staticmethod
    def _d1_d2(
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        dividend_yield: float = 0.0
    ) -> Tuple[float, float]:
        if spot <= 0 or strike <= 0 or volatility <= 0 or time_to_expiry <= 0:
            raise ValueError("Spot, strike, volatility, and time to expiry must be strictly positive.")
        
        sigma_sqrt_t = volatility * math.sqrt(time_to_expiry)
        d1 = (math.log(spot / strike) + (risk_free_rate - dividend_yield + 0.5 * volatility ** 2) * time_to_expiry) / sigma_sqrt_t
        d2 = d1 - sigma_sqrt_t
        return d1, d2

    @classmethod
    def price_and_greeks(
        cls,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        dividend_yield: float = 0.0,
        option_type: str = "call"
    ) -> Dict[str, Any]:
        """
        Calculate analytical price and full Greek sensitivities.
        Time to expiry in years. Volatility and rates in decimal (e.g. 0.20 = 20%).
        """
        is_call = option_type.lower() == "call"
        d1, d2 = cls._d1_d2(spot, strike, time_to_expiry, risk_free_rate, volatility, dividend_yield)
        sqrt_t = math.sqrt(time_to_expiry)
        exp_qt = math.exp(-dividend_yield * time_to_expiry)
        exp_rt = math.exp(-risk_free_rate * time_to_expiry)
        pdf_d1 = norm.pdf(d1)

        if is_call:
            price = spot * exp_qt * norm.cdf(d1) - strike * exp_rt * norm.cdf(d2)
            delta = exp_qt * norm.cdf(d1)
            theta_annual = (
                - (spot * exp_qt * pdf_d1 * volatility) / (2 * sqrt_t)
                - risk_free_rate * strike * exp_rt * norm.cdf(d2)
                + dividend_yield * spot * exp_qt * norm.cdf(d1)
            )
            rho = strike * time_to_expiry * exp_rt * norm.cdf(d2) * 0.01
            charm = (
                dividend_yield * exp_qt * norm.cdf(d1)
                - exp_qt * pdf_d1 * (2 * (risk_free_rate - dividend_yield) * time_to_expiry - d2 * volatility * sqrt_t) / (2 * time_to_expiry * volatility * sqrt_t)
            )
        else:
            price = strike * exp_rt * norm.cdf(-d2) - spot * exp_qt * norm.cdf(-d1)
            delta = -exp_qt * norm.cdf(-d1)
            theta_annual = (
                - (spot * exp_qt * pdf_d1 * volatility) / (2 * sqrt_t)
                + risk_free_rate * strike * exp_rt * norm.cdf(-d2)
                - dividend_yield * spot * exp_qt * norm.cdf(-d1)
            )
            rho = -strike * time_to_expiry * exp_rt * norm.cdf(-d2) * 0.01
            charm = (
                - dividend_yield * exp_qt * norm.cdf(-d1)
                - exp_qt * pdf_d1 * (2 * (risk_free_rate - dividend_yield) * time_to_expiry - d2 * volatility * sqrt_t) / (2 * time_to_expiry * volatility * sqrt_t)
            )

        # Shared Greeks
        gamma = (exp_qt * pdf_d1) / (spot * volatility * sqrt_t)
        vega_point = (spot * exp_qt * pdf_d1 * sqrt_t) / 100.0  # per 1% move in vol
        vanna = -exp_qt * pdf_d1 * (d2 / volatility)  # dDelta/dVol
        volga = spot * exp_qt * pdf_d1 * sqrt_t * (d1 * d2 / volatility) / 100.0  # dVega/dVol per 1%

        theta_daily = theta_annual / 365.0

        return {
            "option_type": "call" if is_call else "put",
            "price": round(float(price), 4),
            "delta": round(float(delta), 4),
            "gamma": round(float(gamma), 6),
            "vega": round(float(vega_point), 4),
            "theta_daily": round(float(theta_daily), 4),
            "theta_annual": round(float(theta_annual), 4),
            "rho": round(float(rho), 4),
            "vanna": round(float(vanna), 6),
            "volga": round(float(volga), 6),
            "charm": round(float(charm), 6),
            "intrinsic_value": round(float(max(0.0, spot - strike if is_call else strike - spot)), 4),
            "extrinsic_value": round(float(max(0.0, price - max(0.0, spot - strike if is_call else strike - spot))), 4),
            "d1": round(float(d1), 4),
            "d2": round(float(d2), 4)
        }

    @classmethod
    def implied_volatility(
        cls,
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        dividend_yield: float = 0.0,
        option_type: str = "call"
    ) -> float:
        """Calculate Implied Volatility using Brent's root-finding method."""
        is_call = option_type.lower() == "call"
        intrinsic = max(0.0, spot - strike if is_call else strike - spot)
        if market_price <= intrinsic:
            return 0.001

        def objective(vol: float) -> float:
            res = cls.price_and_greeks(
                spot, strike, time_to_expiry, risk_free_rate, vol, dividend_yield, option_type
            )
            return res["price"] - market_price

        try:
            return float(brentq(objective, 1e-4, 5.0, xtol=1e-5))
        except Exception:
            return 0.20  # Fallback default IV

    @classmethod
    def analyze_strategy_legs(
        cls,
        spot: float,
        legs: List[Dict[str, Any]],
        risk_free_rate: float = 0.045,
        dividend_yield: float = 0.0,
        spot_eval_range_pct: float = 0.30
    ) -> Dict[str, Any]:
        """
        Analyze multi-leg option strategy (e.g. Iron Condor, Straddle, Spread, Collar).
        Each leg: {
            "type": "call" | "put" | "stock",
            "strike": float,
            "expiry_years": float,
            "volatility": float,
            "quantity": int (positive for long, negative for short)
        }
        """
        net_initial_cost = 0.0
        net_delta = 0.0
        net_gamma = 0.0
        net_vega = 0.0
        net_theta = 0.0
        leg_details = []

        for leg in legs:
            qty = leg.get("quantity", 1)
            leg_type = leg.get("type", "call").lower()

            if leg_type == "stock":
                net_initial_cost += spot * qty
                net_delta += 1.0 * qty
                leg_details.append({
                    "leg": "underlying_shares",
                    "quantity": qty,
                    "price": spot,
                    "delta": 1.0 * qty,
                    "gamma": 0.0,
                    "vega": 0.0,
                    "theta": 0.0
                })
                continue

            strike = leg["strike"]
            expiry = leg.get("expiry_years", 30 / 365.0)
            vol = leg.get("volatility", 0.25)
            metrics = cls.price_and_greeks(spot, strike, expiry, risk_free_rate, vol, dividend_yield, leg_type)
            premium = metrics["price"]
            net_initial_cost += premium * qty
            net_delta += metrics["delta"] * qty
            net_gamma += metrics["gamma"] * qty
            net_vega += metrics["vega"] * qty
            net_theta += metrics["theta_daily"] * qty

            leg_details.append({
                "leg": f"{'Long' if qty > 0 else 'Short'} {abs(qty)}x {strike} {leg_type.upper()}",
                "quantity": qty,
                "strike": strike,
                "price": premium,
                "delta": round(metrics["delta"] * qty, 4),
                "gamma": round(metrics["gamma"] * qty, 6),
                "vega": round(metrics["vega"] * qty, 4),
                "theta_daily": round(metrics["theta_daily"] * qty, 4)
            })

        # Calculate PnL across spot price range
        low_spot = max(1.0, spot * (1.0 - spot_eval_range_pct))
        high_spot = spot * (1.0 + spot_eval_range_pct)
        spot_grid = np.linspace(low_spot, high_spot, 61)
        pnl_at_expiry = []

        for s in spot_grid:
            payoff_val = 0.0
            for leg in legs:
                qty = leg.get("quantity", 1)
                leg_type = leg.get("type", "call").lower()
                if leg_type == "stock":
                    payoff_val += (s - spot) * qty
                elif leg_type == "call":
                    payoff_val += (max(0.0, s - leg["strike"]) - leg.get("custom_premium", leg.get("price", 0.0))) * qty
                elif leg_type == "put":
                    payoff_val += (max(0.0, leg["strike"] - s) - leg.get("custom_premium", leg.get("price", 0.0))) * qty
            pnl_at_expiry.append(float(payoff_val))

        max_profit = float(np.max(pnl_at_expiry))
        max_loss = float(np.min(pnl_at_expiry))

        # Detect breakeven crossings
        breakevens = []
        for i in range(len(spot_grid) - 1):
            if (pnl_at_expiry[i] <= 0 and pnl_at_expiry[i+1] >= 0) or (pnl_at_expiry[i] >= 0 and pnl_at_expiry[i+1] <= 0):
                # linear interpolation
                x0, x1 = spot_grid[i], spot_grid[i+1]
                y0, y1 = pnl_at_expiry[i], pnl_at_expiry[i+1]
                if y1 != y0:
                    be = x0 - y0 * (x1 - x0) / (y1 - y0)
                    breakevens.append(round(float(be), 2))

        return {
            "spot": spot,
            "net_debit_credit": round(float(net_initial_cost), 4),
            "structure": "Debit" if net_initial_cost > 0 else "Credit",
            "net_delta": round(float(net_delta), 4),
            "net_gamma": round(float(net_gamma), 6),
            "net_vega": round(float(net_vega), 4),
            "net_theta_daily": round(float(net_theta), 4),
            "max_profit": round(max_profit, 2) if max_profit < 1e8 else "Unlimited",
            "max_loss": round(max_loss, 2) if max_loss > -1e8 else "Unlimited",
            "breakevens": breakevens,
            "legs": leg_details,
            "pnl_curve": {
                "spots": [round(float(x), 2) for x in spot_grid],
                "pnls": [round(float(y), 2) for y in pnl_at_expiry]
            }
        }


# =============================================================================
# 2. FUTURES & COMMODITY ENGINE (Cost-of-Carry, Term Structure & Roll Yield)
# =============================================================================

class FuturesCommodityEngine:
    """
    Quantitative engine for commodity and financial futures:
    Cost-of-carry theoretical pricing, contango vs backwardation term structures,
    annualized roll yield decay/boost, and leverage/margin stress testing.
    """

    @staticmethod
    def theoretical_futures_price(
        spot: float,
        time_to_expiry_years: float,
        risk_free_rate: float,
        storage_cost_annual: float = 0.0,
        convenience_yield_annual: float = 0.0
    ) -> Dict[str, Any]:
        """
        Cost-of-Carry Model: F = S * exp((r + c - y) * T)
        """
        carry_rate = risk_free_rate + storage_cost_annual - convenience_yield_annual
        futures_price = spot * math.exp(carry_rate * time_to_expiry_years)
        basis = spot - futures_price  # Cash - Futures basis convention
        basis_pct = (basis / spot) * 100.0

        return {
            "spot": spot,
            "theoretical_futures_price": round(float(futures_price), 4),
            "net_cost_of_carry_annual_pct": round(float(carry_rate * 100.0), 3),
            "basis": round(float(basis), 4),
            "basis_pct": round(float(basis_pct), 3),
            "regime": "Contango" if futures_price > spot else "Backwardation" if futures_price < spot else "Flat"
        }

    @staticmethod
    def analyze_term_structure(
        curve: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze term structure across multiple contracts.
        Each entry in curve: {"contract": "Front M1", "days_to_expiry": 30, "price": 75.50}
        """
        if len(curve) < 2:
            raise ValueError("Curve must contain at least 2 contracts for term structure analysis.")

        sorted_curve = sorted(curve, key=lambda x: x["days_to_expiry"])
        front = sorted_curve[0]
        deferred = sorted_curve[1]
        back = sorted_curve[-1]

        # 1-month / Front-to-next roll yield
        day_diff = max(1, deferred["days_to_expiry"] - front["days_to_expiry"])
        price_diff = front["price"] - deferred["price"]
        # In backwardation (front > deferred), roll yield is positive for longs (buying back cheaper)
        roll_yield_pct = (price_diff / deferred["price"]) * (365.0 / day_diff) * 100.0

        # Term structure slope (annualized spread between front and back)
        total_days = max(1, back["days_to_expiry"] - front["days_to_expiry"])
        total_slope_pct = ((back["price"] - front["price"]) / front["price"]) * (365.0 / total_days) * 100.0

        is_contango = back["price"] > front["price"]
        regime = "Contango (Headwind for Longs)" if is_contango else "Backwardation (Tailwind for Longs)"

        spreads = []
        for i in range(len(sorted_curve) - 1):
            c1, c2 = sorted_curve[i], sorted_curve[i+1]
            dt = max(1, c2["days_to_expiry"] - c1["days_to_expiry"])
            spr = c2["price"] - c1["price"]
            ann_pct = (spr / c1["price"]) * (365.0 / dt) * 100.0
            spreads.append({
                "pair": f"{c1['contract']} -> {c2['contract']}",
                "spread": round(float(spr), 3),
                "annualized_carry_pct": round(float(ann_pct), 2),
                "structure": "Contango" if spr > 0 else "Backwardation"
            })

        return {
            "curve_regime": regime,
            "is_contango": is_contango,
            "front_month_price": front["price"],
            "deferred_month_price": deferred["price"],
            "back_month_price": back["price"],
            "front_to_deferred_roll_yield_annual_pct": round(float(roll_yield_pct), 2),
            "curve_slope_annual_pct": round(float(total_slope_pct), 2),
            "spreads": spreads
        }

    @staticmethod
    def calculate_margin_buffer(
        contract_multiplier: float,
        futures_price: float,
        num_contracts: int,
        initial_margin_per_contract: float,
        maintenance_margin_per_contract: float,
        account_equity: float,
        position_side: str = "long"
    ) -> Dict[str, Any]:
        """
        Compute institutional margin risk, leverage ratio, and margin call liquidation points.
        """
        is_long = position_side.lower() == "long"
        total_notional = futures_price * contract_multiplier * abs(num_contracts)
        total_initial_margin = initial_margin_per_contract * abs(num_contracts)
        total_maintenance_margin = maintenance_margin_per_contract * abs(num_contracts)

        leverage = total_notional / account_equity if account_equity > 0 else 999.0
        margin_utilization = (total_initial_margin / account_equity * 100.0) if account_equity > 0 else 100.0
        free_headroom = account_equity - total_maintenance_margin

        # Adverse move in dollars per contract before maintenance margin breached
        max_adverse_equity_loss = account_equity - total_maintenance_margin
        adverse_pts = max_adverse_equity_loss / (contract_multiplier * abs(num_contracts)) if num_contracts != 0 else 0.0

        if is_long:
            margin_call_price = futures_price - adverse_pts
            drop_to_call_pct = (adverse_pts / futures_price) * 100.0
        else:
            margin_call_price = futures_price + adverse_pts
            drop_to_call_pct = (adverse_pts / futures_price) * 100.0

        return {
            "total_notional": round(float(total_notional), 2),
            "effective_leverage": round(float(leverage), 2),
            "margin_utilization_pct": round(float(margin_utilization), 2),
            "account_equity": round(float(account_equity), 2),
            "total_initial_margin": round(float(total_initial_margin), 2),
            "total_maintenance_margin": round(float(total_maintenance_margin), 2),
            "free_margin_headroom": round(float(free_headroom), 2),
            "margin_call_trigger_price": round(float(margin_call_price), 2),
            "max_adverse_move_pct": round(float(drop_to_call_pct), 2),
            "risk_status": "CRITICAL" if margin_utilization > 85.0 else "ELEVATED" if margin_utilization > 60.0 else "HEALTHY"
        }


# =============================================================================
# 3. FIXED INCOME MACRO ENGINE (Duration, Convexity, DV01 & Yield Curve)
# =============================================================================

class FixedIncomeMacroEngine:
    """
    Fixed income analytics for sovereign bonds, corporate credit, and interest rate macro:
    Macaulay & Modified Duration, DV01 ($ per bp), Convexity, and rate shock simulation.
    """

    @classmethod
    def bond_sensitivities(
        cls,
        face_value: float,
        coupon_rate_annual: float,
        yield_to_maturity_annual: float,
        years_to_maturity: float,
        payments_per_year: int = 2
    ) -> Dict[str, Any]:
        """
        Compute dirty price, Macaulay duration, modified duration, convexity, and DV01.
        Rates in decimal (e.g. 0.045 = 4.5%).
        """
        n_periods = int(round(years_to_maturity * payments_per_year))
        c_period = (coupon_rate_annual / payments_per_year) * face_value
        y_period = yield_to_maturity_annual / payments_per_year

        pv_cash_flows = []
        weighted_times = []
        convexity_weights = []

        for t in range(1, n_periods + 1):
            cf = c_period if t < n_periods else c_period + face_value
            discount_factor = (1.0 + y_period) ** (-t)
            pv = cf * discount_factor
            pv_cash_flows.append(pv)
            weighted_times.append(t * pv)
            convexity_weights.append(t * (t + 1) * pv)

        price = sum(pv_cash_flows)
        # Macaulay duration in periods, convert to years
        mac_duration_periods = sum(weighted_times) / price if price > 0 else 0.0
        mac_duration_years = mac_duration_periods / payments_per_year

        # Modified duration
        mod_duration = mac_duration_years / (1.0 + y_period)

        # Convexity in years^2
        convexity_periods = sum(convexity_weights) / (price * ((1.0 + y_period) ** 2)) if price > 0 else 0.0
        convexity_years = convexity_periods / (payments_per_year ** 2)

        # DV01: Dollar value of a 1 basis point shift (+0.01% = 0.0001)
        dv01 = mod_duration * price * 0.0001

        # Rate shock simulations
        shocks_bps = [-200, -100, -50, -25, 25, 50, 100, 200]
        shock_results = {}
        for bps in shocks_bps:
            dy = bps / 10000.0
            # Taylor expansion: dP/P approx - D_mod * dy + 0.5 * Convexity * (dy)^2
            approx_pct_change = (- mod_duration * dy + 0.5 * convexity_years * (dy ** 2)) * 100.0
            new_price = price * (1.0 + approx_pct_change / 100.0)
            shock_results[f"{bps:+d}bps"] = {
                "bps_shift": bps,
                "pct_change": round(float(approx_pct_change), 3),
                "estimated_price": round(float(new_price), 3),
                "dollar_impact": round(float(new_price - price), 3)
            }

        return {
            "price": round(float(price), 3),
            "macaulay_duration_years": round(float(mac_duration_years), 3),
            "modified_duration": round(float(mod_duration), 3),
            "convexity": round(float(convexity_years), 3),
            "dv01_per_bond": round(float(dv01), 4),
            "dv01_per_million_par": round(float(dv01 * (1_000_000.0 / face_value)), 2),
            "rate_shocks": shock_results
        }

    @staticmethod
    def evaluate_yield_curve(
        rates: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Analyze US Treasury yield curve structure.
        Expected rates keys e.g.: {"3M": 4.85, "2Y": 3.95, "5Y": 3.85, "10Y": 4.10, "30Y": 4.40}
        """
        y2 = rates.get("2Y", 4.0)
        y10 = rates.get("10Y", 4.2)
        y3m = rates.get("3M", 4.8)
        y30 = rates.get("30Y", 4.5)

        spread_2_10 = round(float((y10 - y2) * 100.0), 1)  # in bps
        spread_3m_10 = round(float((y10 - y3m) * 100.0), 1)
        spread_10_30 = round(float((y30 - y10) * 100.0), 1)

        is_inverted_2_10 = spread_2_10 < 0
        is_inverted_3m_10 = spread_3m_10 < 0

        # Classification
        if is_inverted_2_10 or is_inverted_3m_10:
            regime = "INVERTED (High Recession Warning)"
        elif spread_2_10 > 150:
            regime = "STEEPENING (Reflation / Expansion Posture)"
        elif spread_2_10 < 30:
            regime = "FLAT (Tightening Policy Restrictive)"
        else:
            regime = "NORMAL (Moderate Upward Slope)"

        return {
            "rates": rates,
            "spread_2y_10y_bps": spread_2_10,
            "spread_3m_10y_bps": spread_3m_10,
            "spread_10y_30y_bps": spread_10_30,
            "curve_regime": regime,
            "is_inverted": is_inverted_2_10 or is_inverted_3m_10,
            "recession_probability_indicator": "HIGH" if (is_inverted_2_10 and is_inverted_3m_10) else "MODERATE" if is_inverted_2_10 else "LOW"
        }


# =============================================================================
# 4. CRYPTO & 24/7 DERIVATIVES ENGINE (Perpetual Funding, Basis & Liquidations)
# =============================================================================

class CryptoDerivativesEngine:
    """
    Continuous 24/7 market microstructure and derivatives engine:
    Perpetual swap funding rate annualization, cash-and-carry basis arbitrage,
    and exchange liquidation cascade vulnerability modeling.
    """

    @staticmethod
    def perpetual_funding_analytics(
        funding_rate_8h_pct: float,
        spot_price: float,
        mark_price: float,
        open_interest_usd: float = 1_000_000_000.0,
        daily_volume_usd: float = 5_000_000_000.0
    ) -> Dict[str, Any]:
        """
        Compute 8h funding yields, annualized APY, premium index, and liquidation pressure.
        funding_rate_8h_pct e.g. 0.01 = 0.01% per 8 hours.
        """
        r8 = funding_rate_8h_pct / 100.0
        simple_annualized_pct = r8 * 3.0 * 365.0 * 100.0
        compound_apy_pct = ((1.0 + r8) ** (3.0 * 365.0) - 1.0) * 100.0

        premium_index_bps = ((mark_price - spot_price) / spot_price) * 10000.0 if spot_price > 0 else 0.0
        oi_to_volume_ratio = open_interest_usd / daily_volume_usd if daily_volume_usd > 0 else 1.0

        # High OI / volume coupled with extreme funding (> +30% APY or < -20% APY) signals liquidation cascade risk
        cascade_risk_score = min(100.0, max(0.0,
            (abs(simple_annualized_pct) / 50.0) * 40.0 + (oi_to_volume_ratio / 0.5) * 60.0
        ))

        return {
            "spot_price": spot_price,
            "mark_price": mark_price,
            "funding_rate_8h_pct": round(float(funding_rate_8h_pct), 5),
            "simple_annualized_pct": round(float(simple_annualized_pct), 2),
            "compound_apy_pct": round(float(compound_apy_pct), 2),
            "premium_index_bps": round(float(premium_index_bps), 2),
            "carry_direction": "Longs Pay Shorts (Bullish Crowding)" if r8 > 0 else "Shorts Pay Longs (Bearish Crowding)",
            "oi_to_volume_ratio": round(float(oi_to_volume_ratio), 3),
            "liquidation_cascade_risk_score": round(float(cascade_risk_score), 1),
            "cascade_alert": "HIGH CASCADE RISK" if cascade_risk_score > 70 else "MODERATE" if cascade_risk_score > 40 else "LOW"
        }

    @staticmethod
    def cash_and_carry_basis(
        spot_price: float,
        futures_price: float,
        days_to_expiry: float,
        maker_taker_fee_pct: float = 0.08,
        borrow_cost_annual_pct: float = 2.0
    ) -> Dict[str, Any]:
        """
        Evaluate Cash-and-Carry Arbitrage (Long Spot + Short Dated Futures).
        """
        if days_to_expiry <= 0:
            raise ValueError("Days to expiry must be positive.")

        gross_basis = futures_price - spot_price
        gross_basis_pct = (gross_basis / spot_price) * 100.0
        gross_annualized_apy = gross_basis_pct * (365.0 / days_to_expiry)

        # Net APY factoring exchange round-trip fees (both legs in/out) & borrowing
        total_fees_pct = (maker_taker_fee_pct * 4) + (borrow_cost_annual_pct * (days_to_expiry / 365.0))
        net_basis_pct = gross_basis_pct - total_fees_pct
        net_annualized_apy = net_basis_pct * (365.0 / days_to_expiry)

        return {
            "spot_price": spot_price,
            "futures_price": futures_price,
            "gross_basis": round(float(gross_basis), 2),
            "gross_basis_pct": round(float(gross_basis_pct), 3),
            "gross_annualized_apy_pct": round(float(gross_annualized_apy), 2),
            "net_annualized_apy_pct": round(float(net_annualized_apy), 2),
            "arbitrage_viable": net_annualized_apy > 5.0  # Above US Treasury hurdle rate
        }

    @staticmethod
    def liquidation_price(
        entry_price: float,
        leverage: float,
        position_side: str = "long",
        maintenance_margin_rate: float = 0.005
    ) -> Dict[str, Any]:
        """
        Calculate isolated/cross-margin liquidation price.
        Formula:
        Long: Entry * (1 - 1/leverage + maintenance_margin_rate)
        Short: Entry * (1 + 1/leverage - maintenance_margin_rate)
        """
        if leverage <= 0:
            raise ValueError("Leverage must be greater than 0.")

        is_long = position_side.lower() == "long"
        inv_lev = 1.0 / leverage

        if is_long:
            liq_price = entry_price * (1.0 - inv_lev + maintenance_margin_rate)
            buffer_pct = ((entry_price - liq_price) / entry_price) * 100.0
        else:
            liq_price = entry_price * (1.0 + inv_lev - maintenance_margin_rate)
            buffer_pct = ((liq_price - entry_price) / entry_price) * 100.0

        return {
            "entry_price": entry_price,
            "leverage": leverage,
            "position_side": "long" if is_long else "short",
            "liquidation_price": round(float(max(0.0, liq_price)), 2),
            "adverse_buffer_pct": round(float(buffer_pct), 2),
            "danger_level": "CRITICAL" if buffer_pct < 5.0 else "ELEVATED" if buffer_pct < 15.0 else "SAFE"
        }


# =============================================================================
# 5. CROSS-ASSET RISK ENGINE (Parametric VaR, CVaR & Crisis Stress-Testing)
# =============================================================================

class CrossAssetRiskEngine:
    """
    Unified multi-asset risk management engine:
    Computes portfolio variance, Parametric VaR (95%/99%), Expected Shortfall (CVaR),
    cross-asset correlation breakdown, and historical crisis stress testing.
    """

    DEFAULT_CRISIS_SCENARIOS = {
        "2008_GFC_CRASH": {
            "name": "2008 Global Financial Crisis Liquidity Shock",
            "equities": -42.0,
            "fixed_income": 12.0,
            "commodities": -52.0,
            "crypto": -65.0,
            "options_vol": 150.0
        },
        "2020_COVID_SHOCK": {
            "name": "2020 March Pandemic Liquidity Meltdown",
            "equities": -34.0,
            "fixed_income": 6.0,
            "commodities": -58.0,
            "crypto": -48.0,
            "options_vol": 210.0
        },
        "2022_FED_RATE_SHOCK": {
            "name": "2022 Historic Fed Tightening & Inflation Surge",
            "equities": -22.0,
            "fixed_income": -16.0,
            "commodities": 35.0,
            "crypto": -68.0,
            "options_vol": 45.0
        },
        "FLASH_CRASH_DELEVERAGING": {
            "name": "Cross-Asset Algorithmic Flash Deleveraging",
            "equities": -12.0,
            "fixed_income": 3.0,
            "commodities": -15.0,
            "crypto": -38.0,
            "options_vol": 110.0
        }
    }

    @classmethod
    def calculate_var_cvar(
        cls,
        portfolio_value: float,
        asset_weights: Dict[str, float],
        asset_volatilities_annual: Dict[str, float],
        correlation_matrix: Dict[str, Dict[str, float]],
        horizon_days: int = 1
    ) -> Dict[str, Any]:
        """
        Parametric Value at Risk (VaR) and Expected Shortfall (CVaR) under normal distribution.
        """
        assets = list(asset_weights.keys())
        n = len(assets)
        w = np.array([asset_weights[a] for a in assets])
        vols = np.array([asset_volatilities_annual[a] for a in assets])

        # Normalize weights to 1.0 if not already
        if abs(np.sum(w) - 1.0) > 1e-4:
            w = w / np.sum(w)

        # Build covariance matrix
        cov = np.zeros((n, n))
        for i, a1 in enumerate(assets):
            for j, a2 in enumerate(assets):
                corr = correlation_matrix.get(a1, {}).get(a2, 1.0 if i == j else 0.2)
                cov[i, j] = corr * vols[i] * vols[j]

        # Daily scaling
        time_scaling = math.sqrt(horizon_days / 252.0)
        port_var_annual = float(np.dot(w.T, np.dot(cov, w)))
        port_vol_annual = math.sqrt(max(1e-8, port_var_annual))
        port_vol_horizon = port_vol_annual * time_scaling

        # VaR z-scores: 95% = 1.6449, 99% = 2.3263
        z_95 = 1.6448536269514722
        z_99 = 2.3263478740408408

        var_95_pct = z_95 * port_vol_horizon * 100.0
        var_99_pct = z_99 * port_vol_horizon * 100.0

        var_95_dollar = portfolio_value * (var_95_pct / 100.0)
        var_99_dollar = portfolio_value * (var_99_pct / 100.0)

        # Expected Shortfall (CVaR) for standard normal: E[X | X > z] = pdf(z) / (1 - alpha)
        cvar_95_pct = (norm.pdf(z_95) / 0.05) * port_vol_horizon * 100.0
        cvar_99_pct = (norm.pdf(z_99) / 0.01) * port_vol_horizon * 100.0

        cvar_95_dollar = portfolio_value * (cvar_95_pct / 100.0)
        cvar_99_dollar = portfolio_value * (cvar_99_pct / 100.0)

        return {
            "portfolio_value": portfolio_value,
            "horizon_days": horizon_days,
            "annualized_portfolio_volatility_pct": round(float(port_vol_annual * 100.0), 2),
            "horizon_volatility_pct": round(float(port_vol_horizon * 100.0), 2),
            "var_95_pct": round(float(var_95_pct), 3),
            "var_95_dollar": round(float(var_95_dollar), 2),
            "var_99_pct": round(float(var_99_pct), 3),
            "var_99_dollar": round(float(var_99_dollar), 2),
            "cvar_95_pct": round(float(cvar_95_pct), 3),
            "cvar_95_dollar": round(float(cvar_95_dollar), 2),
            "cvar_99_pct": round(float(cvar_99_pct), 3),
            "cvar_99_dollar": round(float(cvar_99_dollar), 2)
        }

    @classmethod
    def simulate_crisis_stress(
        cls,
        allocations_usd: Dict[str, float],
        custom_scenarios: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Stress-test portfolio against major macro and liquidity crises.
        allocations_usd keys: "equities", "fixed_income", "commodities", "crypto", "options_overlay"
        """
        scenarios = custom_scenarios or cls.DEFAULT_CRISIS_SCENARIOS
        total_equity = sum(allocations_usd.values())

        stress_results = []
        for s_id, s_data in scenarios.items():
            name = s_data.get("name", s_id)
            dollar_pnl = 0.0
            breakdown = {}

            for asset_class, val in allocations_usd.items():
                shock_pct = s_data.get(asset_class, 0.0)
                asset_pnl = val * (shock_pct / 100.0)
                dollar_pnl += asset_pnl
                breakdown[asset_class] = {
                    "exposure": val,
                    "shock_pct": shock_pct,
                    "pnl_impact": round(float(asset_pnl), 2)
                }

            total_drawdown_pct = (dollar_pnl / total_equity * 100.0) if total_equity > 0 else 0.0
            stress_results.append({
                "scenario_id": s_id,
                "scenario_name": name,
                "projected_pnl_usd": round(float(dollar_pnl), 2),
                "projected_drawdown_pct": round(float(total_drawdown_pct), 2),
                "surviving_equity_usd": round(float(total_equity + dollar_pnl), 2),
                "severity": "CRITICAL BREACH" if total_drawdown_pct < -25.0 else "WARNING" if total_drawdown_pct < -15.0 else "ACCEPTABLE",
                "breakdown": breakdown
            })

        return {
            "total_portfolio_equity": total_equity,
            "scenarios": stress_results
        }
