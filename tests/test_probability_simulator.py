"""
tests/test_probability_simulator.py
Unit and integration tests for Econometric Probability Simulator:
1. Log-normal PDF, CDF, and Standard Deviation Cones (1-sigma, 2-sigma, 3-sigma)
2. Probability of Profit (POP), Expected Value (EV), POMP, POML for options strategies
3. Continuous-time barrier touch probability (first hitting time / reflection principle)
4. Cornish-Fisher expansion for empirical skewness and excess kurtosis (fat tails)
5. Dynamic Target Date PnL interpolation and IV shock shift
6. Cross-asset probability simulations (Equities, Futures, Crypto Perps, Portfolio)
7. Kelly criterion and risk-reward equations
"""

import math
import pytest
import numpy as np

from tools.calc.probability_simulator import (
    EconometricProbabilitySimulator,
    cornish_fisher_quantile,
    hitting_time_touch_probability,
    calculate_kelly_fraction
)


def test_lognormal_pdf_cdf_and_quantiles():
    sim = EconometricProbabilitySimulator()
    spot = 100.0
    vol = 0.20
    t_years = 1.0  # 1 year
    drift = 0.05

    dist = sim.calculate_lognormal_distribution(
        spot=spot,
        volatility=vol,
        time_years=t_years,
        drift=drift,
        num_points=101
    )

    assert "spot_grid" in dist
    assert "pdf" in dist
    assert "cdf" in dist
    assert len(dist["spot_grid"]) == 101

    # Check that PDF integrates to approximately 1
    from scipy.integrate import trapezoid
    integral = trapezoid(dist["pdf"], dist["spot_grid"])
    assert 0.95 <= integral <= 1.05

    # Check 1-sigma, 2-sigma, 3-sigma cones
    cones = dist["sigma_cones"]
    assert cones["minus_1_sigma"] < spot < cones["plus_1_sigma"]
    assert cones["minus_2_sigma"] < cones["minus_1_sigma"]
    assert cones["plus_2_sigma"] > cones["plus_1_sigma"]
    assert cones["minus_3_sigma"] < cones["minus_2_sigma"]
    assert cones["plus_3_sigma"] > cones["plus_2_sigma"]


def test_touch_probability_reflection_principle():
    spot = 100.0
    barrier_up = 110.0
    barrier_down = 90.0
    vol = 0.20
    t_years = 0.25  # 90 days
    drift = 0.045

    p_touch_up = hitting_time_touch_probability(spot, barrier_up, t_years, vol, drift)
    p_touch_down = hitting_time_touch_probability(spot, barrier_down, t_years, vol, drift)

    # Touch probability must be strictly between 0 and 1
    assert 0.0 < p_touch_up < 1.0
    assert 0.0 < p_touch_down < 1.0

    # In Brownian motion, touch probability is always greater than or equal to finish probability
    # e.g. for upward barrier, P(Touch >= 110) >= P(S_T >= 110)
    d1 = (math.log(spot / barrier_up) + (drift + 0.5 * vol**2) * t_years) / (vol * math.sqrt(t_years))
    d2 = d1 - vol * math.sqrt(t_years)
    from scipy.stats import norm
    p_finish_above = norm.cdf(d2)

    assert p_touch_up >= p_finish_above
    # Typically P(touch) is nearly double P(finish ITM) for near-the-money options
    assert p_touch_up > p_finish_above * 1.3


def test_cornish_fisher_fat_tail_adjustment():
    # In standard normal, 95% quantile is approx 1.64485
    z_standard = 1.64485

    # Zero skewness and zero excess kurtosis must reproduce standard quantile
    z_cf_normal = cornish_fisher_quantile(z_standard, skewness=0.0, excess_kurtosis=0.0)
    assert pytest.approx(z_cf_normal, rel=1e-4) == z_standard

    # Negative skewness (typical in equities/crypto crashes) shifts left tail lower
    # For a lower tail (alpha = 0.05, z = -1.64485):
    z_left = -1.64485
    z_cf_skewed = cornish_fisher_quantile(z_left, skewness=-0.6, excess_kurtosis=1.5)
    # The negative quantile becomes more extreme (more negative, representing fatter left tail risk)
    assert z_cf_skewed < z_left


def test_probability_of_profit_options_spread():
    sim = EconometricProbabilitySimulator()
    spot = 100.0
    vol = 0.25
    r = 0.045
    t_years = 45 / 365.0

    # Bull Call Spread: Long 100 Call, Short 105 Call
    legs = [
        {"type": "call", "strike": 100.0, "quantity": 1, "volatility": vol, "expiry_years": t_years},
        {"type": "call", "strike": 105.0, "quantity": -1, "volatility": vol, "expiry_years": t_years}
    ]

    res = sim.simulate_options_strategy_probability(
        spot=spot,
        legs=legs,
        risk_free_rate=r,
        target_days=20,
        iv_shift_pct=0.0
    )

    metrics = res["probability_metrics"]
    assert 0.0 <= metrics["probability_of_profit_pct"] <= 100.0
    assert "econometric_adjusted_pop_pct" in metrics
    assert "expected_value_usd" in metrics
    assert "breakeven_points" in metrics
    assert len(metrics["breakeven_points"]) >= 1

    # Check Target Date curves exist
    target_date = res["target_date_analysis"]
    assert "target_pnl_curve" in target_date
    assert "expiry_pnl_curve" in target_date
    assert "spot_grid" in target_date
    assert len(target_date["target_pnl_curve"]) == len(target_date["spot_grid"])


def test_target_date_iv_shock():
    sim = EconometricProbabilitySimulator()
    spot = 100.0
    vol = 0.30
    t_years = 60 / 365.0

    # Long Straddle: benefits from positive IV shock
    legs = [
        {"type": "call", "strike": 100.0, "quantity": 1, "volatility": vol, "expiry_years": t_years},
        {"type": "put", "strike": 100.0, "quantity": 1, "volatility": vol, "expiry_years": t_years}
    ]

    res_flat = sim.simulate_options_strategy_probability(
        spot=spot, legs=legs, risk_free_rate=0.045, target_days=15, iv_shift_pct=0.0
    )
    res_iv_crush = sim.simulate_options_strategy_probability(
        spot=spot, legs=legs, risk_free_rate=0.045, target_days=15, iv_shift_pct=-20.0
    )
    res_iv_surge = sim.simulate_options_strategy_probability(
        spot=spot, legs=legs, risk_free_rate=0.045, target_days=15, iv_shift_pct=+20.0
    )

    # At spot = 100 on Target Day, higher IV means higher straddle value
    idx_center = len(res_flat["target_date_analysis"]["spot_grid"]) // 2
    pnl_flat = res_flat["target_date_analysis"]["target_pnl_curve"][idx_center]
    pnl_crush = res_iv_crush["target_date_analysis"]["target_pnl_curve"][idx_center]
    pnl_surge = res_iv_surge["target_date_analysis"]["target_pnl_curve"][idx_center]

    assert pnl_surge > pnl_flat > pnl_crush


def test_cross_asset_probability_simulations():
    sim = EconometricProbabilitySimulator()

    # 1. Equity reaching simulation
    eq_res = sim.simulate_equity_probability(
        spot=150.0,
        target_price=175.0,
        stop_loss_price=135.0,
        horizon_days=60,
        volatility=0.28,
        drift=0.08
    )
    assert 0.0 < eq_res["prob_touch_target_pct"] <= 100.0
    assert 0.0 < eq_res["prob_touch_stop_loss_pct"] <= 100.0
    assert "risk_reward_ratio" in eq_res

    # 2. Futures margin call simulation
    fut_res = sim.simulate_futures_margin_risk(
        futures_price=75.0,
        margin_call_trigger_price=68.0,
        days_to_expiry=30,
        volatility=0.35
    )
    assert 0.0 <= fut_res["prob_margin_call_breach_pct"] <= 100.0
    assert fut_res["margin_headroom_pct"] > 0

    # 3. Crypto liquidation simulation
    crypto_res = sim.simulate_crypto_perpetual_risk(
        spot_price=65000.0,
        liquidation_price=58500.0,
        volatility=0.60,
        hours_to_evaluate=72
    )
    assert 0.0 <= crypto_res["prob_liquidation_pct"] <= 100.0
    assert "cascade_probability_score" in crypto_res

    # 4. Multi-Asset Portfolio VaR breach simulation
    port_res = sim.simulate_portfolio_drawdown_probability(
        capital=1_000_000.0,
        annual_vol=0.14,
        annual_drift=0.07,
        days_horizon=252,
        drawdown_thresholds_pct=[5.0, 10.0, 20.0]
    )
    assert "prob_drawdown_5_pct" in port_res
    assert "prob_drawdown_10_pct" in port_res
    assert "prob_drawdown_20_pct" in port_res
    assert port_res["prob_drawdown_5_pct"] >= port_res["prob_drawdown_10_pct"] >= port_res["prob_drawdown_20_pct"]


def test_kelly_criterion_and_expected_value():
    # Win probability 60%, payout ratio 2.0 (Win $2 for every $1 lost)
    f_full, f_half = calculate_kelly_fraction(win_prob=0.60, win_loss_ratio=2.0)
    # Full Kelly: (0.60 * 2 - 0.40) / 2 = (1.2 - 0.4) / 2 = 0.40
    assert pytest.approx(f_full, rel=1e-3) == 0.40
    assert pytest.approx(f_half, rel=1e-3) == 0.20

    # Negative expectation game: Win prob 30%, win_loss_ratio 1.0 -> Kelly must be 0 (no bet)
    f_neg, _ = calculate_kelly_fraction(win_prob=0.30, win_loss_ratio=1.0)
    assert f_neg == 0.0
