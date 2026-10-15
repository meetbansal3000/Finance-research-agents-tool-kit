"""
tools/calc/probability_simulator.py
Econometric Probability & Strategy Simulation Engine for Meridian Terminal.

Incorporates Sensibull-style interactive options analytics and econometric modeling:
1. Analytical Log-Normal Probability Density Function (PDF) & Cumulative Distribution Function (CDF).
2. Standard Deviation Cones (1-sigma 68.27%, 2-sigma 95.45%, 3-sigma 99.73%).
3. Probability of Profit (POP) and Probability of Touch (hitting time reflection principle).
4. Cornish-Fisher Expansion for empirical fat-tail leptokurtosis and negative skewness adjustments.
5. Sensibull Target Date P&L curves with Implied Volatility (IV) shocks and time decay.
6. Probability of Max Profit (POMP) & Probability of Max Loss (POML).
7. Cross-Asset Probability Evaluators (Equities, Futures Margin Breaches, Crypto Liquidation, Portfolio Drawdown).
8. Statistical Expected Value (EV) and Kelly Criterion Position Sizing.
"""

import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy.stats import norm
from scipy.integrate import trapezoid

from tools.calc.derivatives_math import BlackScholesEngine


# =============================================================================
# 1. ECONOMETRIC UTILITIES: CORNISH-FISHER, BARRIER TOUCH & KELLY
# =============================================================================

def cornish_fisher_quantile(z: float, skewness: float = 0.0, excess_kurtosis: float = 0.0) -> float:
    """
    Cornish-Fisher expansion to adjust a standard Gaussian quantile z_alpha for
    higher-order sample skewness (S) and excess kurtosis (K):
    z_CF = z + (S/6)*(z^2 - 1) + (K/24)*(z^3 - 3z) - (S^2/36)*(2z^3 - 5z)
    """
    s = skewness
    k = excess_kurtosis
    z2 = z ** 2
    z3 = z ** 3
    z_cf = z + (s / 6.0) * (z2 - 1.0) + (k / 24.0) * (z3 - 3.0 * z) - (s ** 2 / 36.0) * (2.0 * z3 - 5.0 * z)
    return float(z_cf)


def hitting_time_touch_probability(
    spot: float,
    barrier: float,
    time_years: float,
    volatility: float,
    drift: float = 0.0
) -> float:
    """
    Exact analytical probability that a Geometric Brownian Motion hits a barrier B
    at ANY point during the time horizon [0, T] (First Hitting Time / Reflection Principle).
    """
    if spot <= 0 or barrier <= 0 or time_years <= 0 or volatility <= 0:
        return 0.0

    if spot == barrier:
        return 1.0

    # Log distance to barrier
    h = math.log(barrier / spot)
    sigma_sqrt_t = volatility * math.sqrt(time_years)
    alpha = drift - 0.5 * (volatility ** 2)

    # Exponent factor: 2 * alpha * h / sigma^2
    exp_power = (2.0 * alpha * h) / (volatility ** 2)
    # Guard against numerical overflow in exp
    exp_factor = math.exp(min(50.0, max(-50.0, exp_power)))

    if barrier > spot:
        # Upward barrier
        term1 = norm.cdf((-h + alpha * time_years) / sigma_sqrt_t)
        term2 = exp_factor * norm.cdf((-h - alpha * time_years) / sigma_sqrt_t)
        prob = term1 + term2
    else:
        # Downward barrier
        term1 = norm.cdf((h - alpha * time_years) / sigma_sqrt_t)
        term2 = exp_factor * norm.cdf((h + alpha * time_years) / sigma_sqrt_t)
        prob = term1 + term2

    return float(min(1.0, max(0.0, prob)))


def calculate_kelly_fraction(
    win_prob: float,
    win_loss_ratio: float,
    max_cap: float = 1.0
) -> Tuple[float, float]:
    """
    Kelly Criterion for optimal capital allocation:
    f* = (p * b - q) / b
    where p = win probability, q = 1 - p, b = win/loss ratio (profit / loss).
    Returns (full_kelly, half_kelly).
    """
    if win_loss_ratio <= 0.0 or win_prob <= 0.0 or win_prob >= 1.0:
        return 0.0, 0.0

    q = 1.0 - win_prob
    numerator = win_prob * win_loss_ratio - q
    if numerator <= 0.0:
        return 0.0, 0.0

    f_full = min(max_cap, numerator / win_loss_ratio)
    f_half = f_full / 2.0
    return float(f_full), float(f_half)


# =============================================================================
# 2. ECONOMETRIC PROBABILITY SIMULATOR CLASS
# =============================================================================

class EconometricProbabilitySimulator:
    """
    Institutional Econometric Probability Simulator mirroring Sensibull & Bloomberg OVME.
    Provides probability of profit, expected value, multi-leg target date P&L,
    standard deviation cones, and cross-asset risk distributions.
    """

    def calculate_lognormal_distribution(
        self,
        spot: float,
        volatility: float,
        time_years: float,
        drift: Optional[float] = None,
        num_points: int = 121
    ) -> Dict[str, Any]:
        """
        Compute continuous probability density function (PDF), cumulative distribution (CDF),
        and standard deviation cones for underlying price at horizon T.
        """
        if spot <= 0 or volatility <= 0 or time_years <= 0:
            raise ValueError("Spot, volatility, and time_years must be strictly positive.")

        mu = drift if drift is not None else 0.045  # Default to benchmark risk-free rate
        mu_log = math.log(spot) + (mu - 0.5 * volatility ** 2) * time_years
        sigma_log = volatility * math.sqrt(time_years)

        # Build grid spanning +/- 3.5 standard deviations in log space
        min_spot = max(0.01, math.exp(mu_log - 3.5 * sigma_log))
        max_spot = math.exp(mu_log + 3.5 * sigma_log)
        spot_grid = np.linspace(min_spot, max_spot, num_points)

        # Lognormal PDF: f(S) = (1 / (S * sigma_log * sqrt(2*pi))) * exp(- (ln(S) - mu_log)^2 / (2 * sigma_log^2))
        pdf = (1.0 / (spot_grid * sigma_log * math.sqrt(2 * math.pi))) * np.exp(
            - ((np.log(spot_grid) - mu_log) ** 2) / (2.0 * sigma_log ** 2)
        )

        # Lognormal CDF
        cdf = norm.cdf((np.log(spot_grid) - mu_log) / sigma_log)

        # Calculate exact standard deviation cones (1-sigma: 68.27%, 2-sigma: 95.45%, 3-sigma: 99.73%)
        cones = {
            "minus_3_sigma": round(float(math.exp(mu_log - 3.0 * sigma_log)), 2),
            "minus_2_sigma": round(float(math.exp(mu_log - 2.0 * sigma_log)), 2),
            "minus_1_sigma": round(float(math.exp(mu_log - 1.0 * sigma_log)), 2),
            "median_expected": round(float(math.exp(mu_log)), 2),
            "mean_expected": round(float(spot * math.exp(mu * time_years)), 2),
            "plus_1_sigma": round(float(math.exp(mu_log + 1.0 * sigma_log)), 2),
            "plus_2_sigma": round(float(math.exp(mu_log + 2.0 * sigma_log)), 2),
            "plus_3_sigma": round(float(math.exp(mu_log + 3.0 * sigma_log)), 2),
        }

        return {
            "spot_grid": [round(float(s), 2) for s in spot_grid],
            "pdf": [float(p) for p in pdf],
            "cdf": [float(c) for c in cdf],
            "sigma_cones": cones,
            "parameters": {
                "spot": spot,
                "volatility": volatility,
                "time_years": time_years,
                "drift": mu,
                "mu_log": mu_log,
                "sigma_log": sigma_log
            }
        }

    def simulate_options_strategy_probability(
        self,
        spot: float,
        legs: List[Dict[str, Any]],
        risk_free_rate: float = 0.045,
        dividend_yield: float = 0.0,
        custom_drift: Optional[float] = None,
        skewness: float = -0.45,
        kurtosis: float = 1.80,
        target_days: int = 0,
        iv_shift_pct: float = 0.0,
        num_grid_points: int = 151
    ) -> Dict[str, Any]:
        """
        Sensibull-Style Interactive Options Strategy Probability Simulation.
        Calculates:
        - Probability of Profit (POP %) under Risk-Neutral & Econometric Drift
        - Econometrically adjusted POP using Cornish-Fisher fat-tail expansion
        - Probability of Touch for each Breakeven point
        - Sensibull Target Date PnL curve vs Expiration PnL curve
        - Statistical Expected Value (EV in $USD)
        - Probability of Max Profit (POMP) & Probability of Max Loss (POML)
        - Kelly Criterion optimal position sizing fraction
        """
        if not legs:
            raise ValueError("Must provide at least one option or stock leg.")

        # Determine strategy expiration horizon (use maximum expiry across legs)
        max_expiry = max(leg.get("expiry_years", 30 / 365.0) for leg in legs)
        weighted_vol = float(np.mean([leg.get("volatility", 0.25) for leg in legs]))
        drift = custom_drift if custom_drift is not None else (risk_free_rate - dividend_yield)

        # Baseline Strategy Greeks and Expiration Payoff
        strat_analysis = BlackScholesEngine.analyze_strategy_legs(
            spot=spot,
            legs=legs,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
            spot_eval_range_pct=0.35
        )

        # Continuous probability distribution for the underlying
        dist = self.calculate_lognormal_distribution(
            spot=spot,
            volatility=weighted_vol,
            time_years=max_expiry,
            drift=drift,
            num_points=num_grid_points
        )
        spot_grid = np.array(dist["spot_grid"])
        pdf = np.array(dist["pdf"])
        cdf = np.array(dist["cdf"])

        # 1. Compute Payoff at Expiration across the exact continuous grid
        expiry_pnls = []
        for s in spot_grid:
            payoff_val = 0.0
            for leg in legs:
                qty = leg.get("quantity", 1)
                leg_type = leg.get("type", "call").lower()
                prem = float(leg.get("custom_premium", leg.get("price", 0.0)))
                if leg_type == "stock":
                    payoff_val += (s - spot) * qty
                elif leg_type == "call":
                    payoff_val += (max(0.0, s - leg["strike"]) - prem) * qty
                elif leg_type == "put":
                    payoff_val += (max(0.0, leg["strike"] - s) - prem) * qty
            expiry_pnls.append(float(payoff_val))
        expiry_pnls = np.array(expiry_pnls)

        # 2. Sensibull Target Date P&L Curve (with IV Shift)
        target_t_years = target_days / 365.0
        effective_iv_multiplier = 1.0 + (iv_shift_pct / 100.0)

        target_pnls = []
        for s in spot_grid:
            t_val = 0.0
            for leg in legs:
                qty = leg.get("quantity", 1)
                leg_type = leg.get("type", "call").lower()
                prem = float(leg.get("custom_premium", leg.get("price", 0.0)))

                if leg_type == "stock":
                    t_val += (s - spot) * qty
                else:
                    leg_expiry = leg.get("expiry_years", max_expiry)
                    rem_time = max(1e-4, leg_expiry - target_t_years)
                    adj_vol = max(0.01, leg.get("volatility", weighted_vol) * effective_iv_multiplier)
                    strike = leg["strike"]

                    if rem_time <= 1e-4:
                        # Expired by target date
                        intrin = max(0.0, s - strike) if leg_type == "call" else max(0.0, strike - s)
                        t_val += (intrin - prem) * qty
                    else:
                        greeks = BlackScholesEngine.price_and_greeks(
                            spot=s,
                            strike=strike,
                            time_to_expiry=rem_time,
                            risk_free_rate=risk_free_rate,
                            volatility=adj_vol,
                            dividend_yield=dividend_yield,
                            option_type=leg_type
                        )
                        t_val += (greeks["price"] - prem) * qty
            target_pnls.append(float(t_val))

        # 3. Detect Exact Breakeven Points
        breakevens = []
        for i in range(len(spot_grid) - 1):
            if (expiry_pnls[i] <= 0 and expiry_pnls[i+1] >= 0) or (expiry_pnls[i] >= 0 and expiry_pnls[i+1] <= 0):
                x0, x1 = spot_grid[i], spot_grid[i+1]
                y0, y1 = expiry_pnls[i], expiry_pnls[i+1]
                if y1 != y0:
                    be = x0 - y0 * (x1 - x0) / (y1 - y0)
                    breakevens.append(round(float(be), 2))

        # 4. Compute Probability of Profit (POP) via Numerical Integration
        profit_mask = expiry_pnls > 0.0
        if np.any(profit_mask):
            pop_raw = trapezoid(pdf[profit_mask], spot_grid[profit_mask])
            pop_pct = round(float(min(100.0, max(0.0, pop_raw * 100.0))), 2)
        else:
            pop_pct = 0.0

        # 5. Econometric Fat-Tail POP Adjustment (Cornish-Fisher)
        # Convert POP to standard normal quantile, apply Cornish-Fisher shift, convert back
        if 0.5 < pop_pct < 99.5:
            z_pop = norm.ppf(pop_pct / 100.0)
            z_cf = cornish_fisher_quantile(z_pop, skewness=skewness, excess_kurtosis=kurtosis)
            pop_econometric_pct = round(float(min(99.9, max(0.1, norm.cdf(z_cf) * 100.0))), 2)
        else:
            pop_econometric_pct = pop_pct

        # 6. Touch Probabilities for Breakeven Points (Sensibull "Chance of Touching")
        be_touch_probs = {}
        for be in breakevens:
            p_touch = hitting_time_touch_probability(
                spot=spot,
                barrier=be,
                time_years=max_expiry,
                volatility=weighted_vol,
                drift=drift
            )
            be_touch_probs[f"${be:,.2f}"] = round(p_touch * 100.0, 1)

        # 7. Probability of Max Profit (POMP) & Probability of Max Loss (POML)
        max_profit = float(np.max(expiry_pnls))
        min_loss = float(np.min(expiry_pnls))
        tolerance = max(0.01, 0.02 * (max_profit - min_loss))

        max_profit_mask = expiry_pnls >= (max_profit - tolerance)
        max_loss_mask = expiry_pnls <= (min_loss + tolerance)

        pomp_pct = round(float(trapezoid(pdf[max_profit_mask], spot_grid[max_profit_mask]) * 100.0), 1) if np.any(max_profit_mask) else 0.0
        poml_pct = round(float(trapezoid(pdf[max_loss_mask], spot_grid[max_loss_mask]) * 100.0), 1) if np.any(max_loss_mask) else 0.0

        # 8. Statistical Expected Value (EV)
        expected_value = float(trapezoid(expiry_pnls * pdf, spot_grid))

        # Expected Profit given profit and Expected Loss given loss
        avg_win = float(np.mean(expiry_pnls[profit_mask])) if np.any(profit_mask) else 0.0
        avg_loss = float(abs(np.mean(expiry_pnls[~profit_mask]))) if np.any(~profit_mask) else 1.0
        win_loss_ratio = round(avg_win / max(1e-4, avg_loss), 2)

        # Kelly Criterion
        f_full, f_half = calculate_kelly_fraction(pop_pct / 100.0, win_loss_ratio, max_cap=0.50)

        return {
            "spot": spot,
            "horizon_days": int(round(max_expiry * 365)),
            "target_days": target_days,
            "iv_shift_pct": iv_shift_pct,
            "probability_metrics": {
                "probability_of_profit_pct": pop_pct,
                "econometric_adjusted_pop_pct": pop_econometric_pct,
                "prob_max_profit_pct": pomp_pct,
                "prob_max_loss_pct": poml_pct,
                "expected_value_usd": round(expected_value, 2),
                "breakeven_points": breakevens,
                "breakeven_touch_probabilities": be_touch_probs,
                "win_loss_ratio": win_loss_ratio,
                "kelly_fraction_full_pct": round(f_full * 100.0, 1),
                "kelly_fraction_half_pct": round(f_half * 100.0, 1),
                "max_profit_usd": round(max_profit, 2),
                "max_loss_usd": round(min_loss, 2)
            },
            "sigma_cones": dist["sigma_cones"],
            "target_date_analysis": {
                "spot_grid": [round(float(s), 2) for s in spot_grid],
                "expiry_pnl_curve": [round(float(p), 2) for p in expiry_pnls],
                "target_pnl_curve": [round(float(p), 2) for p in target_pnls],
                "pdf_distribution": [float(p) for p in pdf]
            },
            "greeks_summary": {
                "net_debit_credit": strat_analysis["net_debit_credit"],
                "structure": strat_analysis["structure"],
                "net_delta": strat_analysis["net_delta"],
                "net_gamma": strat_analysis["net_gamma"],
                "net_vega": strat_analysis["net_vega"],
                "net_theta_daily": strat_analysis["net_theta_daily"]
            }
        }

    # =========================================================================
    # 3. CROSS-ASSET PROBABILITY SIMULATORS (Equities, Futures, Crypto, Portfolio)
    # =========================================================================

    def simulate_equity_probability(
        self,
        spot: float,
        target_price: float,
        stop_loss_price: float,
        horizon_days: int = 60,
        volatility: float = 0.28,
        drift: float = 0.08,
        skewness: float = -0.40,
        kurtosis: float = 1.80
    ) -> Dict[str, Any]:
        """
        Econometric probability simulation for single-stock equity positions.
        Computes probability of touching target vs touching stop-loss,
        terminal distribution, and risk-reward ratios.
        """
        t_years = horizon_days / 365.0
        p_touch_target = hitting_time_touch_probability(spot, target_price, t_years, volatility, drift)
        p_touch_stop = hitting_time_touch_probability(spot, stop_loss_price, t_years, volatility, drift)

        # Terminal probability P(S_T >= Target)
        sigma_sqrt_t = volatility * math.sqrt(t_years)
        mu_log = math.log(spot) + (drift - 0.5 * volatility ** 2) * t_years
        z_target = (math.log(target_price) - mu_log) / sigma_sqrt_t
        p_terminal_target = 1.0 - norm.cdf(z_target)

        # Cornish-Fisher adjustment for terminal target
        z_cf = cornish_fisher_quantile(z_target, skewness=skewness, excess_kurtosis=kurtosis)
        p_terminal_target_adj = 1.0 - norm.cdf(z_cf)

        upside_dollars = target_price - spot
        downside_dollars = spot - stop_loss_price
        rr_ratio = round(upside_dollars / max(0.01, downside_dollars), 2)

        return {
            "spot": spot,
            "target_price": target_price,
            "stop_loss_price": stop_loss_price,
            "horizon_days": horizon_days,
            "prob_touch_target_pct": round(p_touch_target * 100.0, 1),
            "prob_touch_stop_loss_pct": round(p_touch_stop * 100.0, 1),
            "prob_close_above_target_pct": round(p_terminal_target * 100.0, 1),
            "econometric_prob_above_target_pct": round(p_terminal_target_adj * 100.0, 1),
            "risk_reward_ratio": rr_ratio,
            "target_upside_pct": round(((target_price - spot) / spot) * 100.0, 2),
            "stop_loss_pct": round(((stop_loss_price - spot) / spot) * 100.0, 2)
        }

    def simulate_futures_margin_risk(
        self,
        futures_price: float,
        margin_call_trigger_price: float,
        days_to_expiry: int = 30,
        volatility: float = 0.35,
        drift: float = 0.045
    ) -> Dict[str, Any]:
        """
        Probability of encountering an exchange maintenance margin call before contract expiry/roll.
        """
        t_years = days_to_expiry / 365.0
        p_margin_call = hitting_time_touch_probability(
            spot=futures_price,
            barrier=margin_call_trigger_price,
            time_years=t_years,
            volatility=volatility,
            drift=drift
        )
        headroom_pct = abs((futures_price - margin_call_trigger_price) / futures_price) * 100.0

        return {
            "futures_price": futures_price,
            "margin_call_trigger_price": margin_call_trigger_price,
            "days_to_expiry": days_to_expiry,
            "prob_margin_call_breach_pct": round(p_margin_call * 100.0, 1),
            "margin_headroom_pct": round(headroom_pct, 2),
            "risk_level": "CRITICAL" if p_margin_call > 0.20 else "ELEVATED" if p_margin_call > 0.08 else "SAFE"
        }

    def simulate_crypto_perpetual_risk(
        self,
        spot_price: float,
        liquidation_price: float,
        volatility: float = 0.60,
        hours_to_evaluate: int = 72,
        drift: float = 0.0
    ) -> Dict[str, Any]:
        """
        Probability of 24/7 continuous liquidation engine triggering over an N-hour window.
        Uses fat-tailed continuous reflection mechanics.
        """
        t_years = hours_to_evaluate / (24.0 * 365.0)
        p_liq = hitting_time_touch_probability(
            spot=spot_price,
            barrier=liquidation_price,
            time_years=t_years,
            volatility=volatility,
            drift=drift
        )
        buffer_pct = abs((spot_price - liquidation_price) / spot_price) * 100.0
        cascade_score = min(100.0, p_liq * 100.0 * 1.5)

        return {
            "spot_price": spot_price,
            "liquidation_price": liquidation_price,
            "hours_evaluated": hours_to_evaluate,
            "prob_liquidation_pct": round(p_liq * 100.0, 2),
            "adverse_buffer_pct": round(buffer_pct, 2),
            "cascade_probability_score": round(cascade_score, 1),
            "status": "IMMINENT_LIQUIDATION_RISK" if p_liq > 0.15 else "WARNING" if p_liq > 0.05 else "NORMAL"
        }

    def simulate_portfolio_drawdown_probability(
        self,
        capital: float,
        annual_vol: float,
        annual_drift: float = 0.07,
        days_horizon: int = 252,
        drawdown_thresholds_pct: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Analytical probability of portfolio experiencing drawdowns of X% over the horizon.
        """
        if drawdown_thresholds_pct is None:
            drawdown_thresholds_pct = [5.0, 10.0, 15.0, 20.0]

        t_years = days_horizon / 252.0
        res = {
            "capital_usd": capital,
            "annual_volatility_pct": round(annual_vol * 100.0, 2),
            "annual_drift_pct": round(annual_drift * 100.0, 2),
            "days_horizon": days_horizon
        }

        for dd in drawdown_thresholds_pct:
            barrier = capital * (1.0 - dd / 100.0)
            p_touch = hitting_time_touch_probability(
                spot=capital,
                barrier=barrier,
                time_years=t_years,
                volatility=annual_vol,
                drift=annual_drift
            )
            res[f"prob_drawdown_{int(dd)}_pct"] = round(p_touch * 100.0, 1)

        return res
