"""
tests/test_derivatives_math.py - Quantitative Mathematical Verification Suite (Part 2)
Tests all financial models across:
1. Black-Scholes-Merton Pricing, Greeks (Delta, Gamma, Vega, Theta, Rho), and IV Solver
2. Multi-Leg Options Payoff Analyzer (Spreads, Condors, Covered Calls)
3. Cost-of-Carry Futures Pricing, Term Structure Curves, & Margin Buffers
4. Fixed Income Duration, Convexity, DV01, & Treasury Curve Inversion Modeling
5. Crypto Perpetual Funding Rates, Basis Arbitrage, & Liquidation Thresholds
6. Cross-Asset Parametric VaR, CVaR (Expected Shortfall), & Crisis Stress Testing
"""

import math
import pytest
import numpy as np

from tools.calc.derivatives_math import (
    BlackScholesEngine,
    FuturesCommodityEngine,
    FixedIncomeMacroEngine,
    CryptoDerivativesEngine,
    CrossAssetRiskEngine,
)


# =============================================================================
# 1. BLACK-SCHOLES OPTIONS ENGINE TESTS
# =============================================================================

def test_black_scholes_call_and_put_pricing():
    """Verify BSM prices against known analytical benchmarks and Put-Call Parity."""
    spot = 100.0
    strike = 100.0
    t = 1.0  # 1 year
    r = 0.05  # 5%
    vol = 0.20  # 20%
    q = 0.0  # zero dividend

    call_res = BlackScholesEngine.price_and_greeks(spot, strike, t, r, vol, q, "call")
    put_res = BlackScholesEngine.price_and_greeks(spot, strike, t, r, vol, q, "put")

    # ATM 1Y Call at 5% rate and 20% vol is approximately $10.45
    assert pytest.approx(call_res["price"], abs=0.1) == 10.45
    # ATM 1Y Put at 5% rate and 20% vol is approximately $5.57
    assert pytest.approx(put_res["price"], abs=0.1) == 5.57

    # Put-Call Parity: C - P = S - K * exp(-r * T)
    parity_lhs = call_res["price"] - put_res["price"]
    parity_rhs = spot - strike * math.exp(-r * t)
    assert pytest.approx(parity_lhs, abs=1e-3) == parity_rhs


def test_black_scholes_greeks_properties():
    """Verify standard Greek boundaries and sensitivity signs."""
    spot = 150.0
    strike = 150.0
    t = 0.5  # 6 months
    r = 0.04
    vol = 0.25

    c = BlackScholesEngine.price_and_greeks(spot, strike, t, r, vol, option_type="call")
    p = BlackScholesEngine.price_and_greeks(spot, strike, t, r, vol, option_type="put")

    # Call Delta between 0 and 1, Put Delta between -1 and 0
    assert 0.0 < c["delta"] < 1.0
    assert -1.0 < p["delta"] < 0.0
    # Delta difference equals exp(-q*t) = 1.0
    assert pytest.approx(c["delta"] - p["delta"], abs=1e-3) == 1.0

    # Gamma is strictly positive for long calls and long puts and identical
    assert c["gamma"] > 0
    assert pytest.approx(c["gamma"], abs=1e-5) == p["gamma"]

    # Vega is strictly positive and identical for call and put
    assert c["vega"] > 0
    assert pytest.approx(c["vega"], abs=1e-4) == p["vega"]

    # Theta daily decay is negative for standard long options
    assert c["theta_daily"] < 0
    assert p["theta_daily"] < 0


def test_implied_volatility_solver():
    """Verify Brent's root-finding IV solver accurately recovers input volatility."""
    spot = 200.0
    strike = 205.0
    t = 45 / 365.0
    r = 0.045
    true_vol = 0.32

    # Calculate analytical price with known volatility
    eval_call = BlackScholesEngine.price_and_greeks(spot, strike, t, r, true_vol, option_type="call")
    market_price = eval_call["price"]

    # Invert price to recover volatility
    solved_iv = BlackScholesEngine.implied_volatility(market_price, spot, strike, t, r, option_type="call")
    assert pytest.approx(solved_iv, abs=1e-3) == true_vol


def test_multi_leg_strategy_analyzer():
    """Verify multi-leg strategy analysis (e.g. Bull Call Spread)."""
    spot = 100.0
    # Bull Call Spread: Long 95 Call (+1), Short 105 Call (-1)
    legs = [
        {"type": "call", "strike": 95.0, "expiry_years": 0.25, "volatility": 0.20, "quantity": 1},
        {"type": "call", "strike": 105.0, "expiry_years": 0.25, "volatility": 0.20, "quantity": -1}
    ]

    analysis = BlackScholesEngine.analyze_strategy_legs(spot, legs, risk_free_rate=0.04)

    assert analysis["structure"] == "Debit"
    assert analysis["net_debit_credit"] > 0.0  # Net debit
    assert analysis["net_delta"] > 0.0         # Bullish delta
    assert analysis["max_profit"] > 0.0
    assert analysis["max_loss"] < 0.0
    assert len(analysis["breakevens"]) == 1
    # Breakeven should lie between 95 and 105
    assert 95.0 < analysis["breakevens"][0] < 105.0


# =============================================================================
# 2. FUTURES & COMMODITY ENGINE TESTS
# =============================================================================

def test_cost_of_carry_and_basis():
    """Verify theoretical futures price and contango/backwardation basis."""
    spot = 80.0
    t = 0.5
    r = 0.05
    c = 0.02  # 2% storage
    y = 0.01  # 1% convenience yield

    res = FuturesCommodityEngine.theoretical_futures_price(spot, t, r, c, y)

    # Net carry is positive (0.05 + 0.02 - 0.01 = 0.06), so Futures > Spot (Contango)
    assert res["theoretical_futures_price"] > spot
    assert res["regime"] == "Contango"
    assert res["net_cost_of_carry_annual_pct"] == 6.0


def test_futures_term_structure_roll_yield():
    """Verify term structure slope and annualized roll yield."""
    curve = [
        {"contract": "M1 (Front)", "days_to_expiry": 30, "price": 75.0},
        {"contract": "M2 (Deferred)", "days_to_expiry": 60, "price": 76.5},
        {"contract": "M6 (Back)", "days_to_expiry": 180, "price": 81.0}
    ]

    ts = FuturesCommodityEngine.analyze_term_structure(curve)

    assert ts["is_contango"] is True
    assert "Contango" in ts["curve_regime"]
    # In Contango, roll yield for long positions is negative (paying more for deferred)
    assert ts["front_to_deferred_roll_yield_annual_pct"] < 0
    assert ts["curve_slope_annual_pct"] > 0
    assert len(ts["spreads"]) == 2


def test_futures_margin_buffer_and_call_price():
    """Verify institutional margin requirements and margin call trigger prices."""
    contract_multiplier = 50.0  # ES
    futures_price = 5000.0
    num_contracts = 2
    initial_margin = 12500.0
    maintenance_margin = 11250.0
    account_equity = 50000.0

    margin_analysis = FuturesCommodityEngine.calculate_margin_buffer(
        contract_multiplier=contract_multiplier,
        futures_price=futures_price,
        num_contracts=num_contracts,
        initial_margin_per_contract=initial_margin,
        maintenance_margin_per_contract=maintenance_margin,
        account_equity=account_equity,
        position_side="long"
    )

    # Total notional = 5000 * 50 * 2 = $500,000
    assert margin_analysis["total_notional"] == 500_000.0
    # Leverage = $500,000 / $50,000 = 10.0x
    assert margin_analysis["effective_leverage"] == 10.0
    # Initial margin = $25,000, Maintenance = $22,500
    assert margin_analysis["total_initial_margin"] == 25_000.0
    assert margin_analysis["total_maintenance_margin"] == 22_500.0
    # Long margin call trigger price must be lower than current futures price
    assert margin_analysis["margin_call_trigger_price"] < futures_price
    assert margin_analysis["risk_status"] == "HEALTHY"


# =============================================================================
# 3. FIXED INCOME & MACRO ENGINE TESTS
# =============================================================================

def test_bond_sensitivities_and_convexity():
    """Verify Macaulay duration, modified duration, convexity, and DV01."""
    face = 1000.0
    coupon = 0.05  # 5% coupon
    ytm = 0.05     # 5% yield (trading at par)
    maturity = 10.0  # 10 years
    freq = 2

    sens = FixedIncomeMacroEngine.bond_sensitivities(face, coupon, ytm, maturity, freq)

    # At par, price should equal face value $1000.00
    assert pytest.approx(sens["price"], abs=0.5) == 1000.0
    # Macaulay duration must be less than maturity for coupon bonds
    assert 0.0 < sens["macaulay_duration_years"] < maturity
    # Modified duration = Mac duration / (1 + y/2)
    expected_mod = sens["macaulay_duration_years"] / (1.0 + ytm / freq)
    assert pytest.approx(sens["modified_duration"], abs=1e-3) == expected_mod
    # Convexity must be positive
    assert sens["convexity"] > 0
    # DV01 must be positive
    assert sens["dv01_per_bond"] > 0

    # Rate shocks: +100 bps should decrease price, -100 bps should increase price
    shocks = sens["rate_shocks"]
    assert shocks["+100bps"]["pct_change"] < 0
    assert shocks["-100bps"]["pct_change"] > 0


def test_yield_curve_evaluation_regimes():
    """Verify yield curve inversion and steepening detection."""
    # Normal curve
    normal_rates = {"3M": 3.5, "2Y": 3.8, "5Y": 4.1, "10Y": 4.5, "30Y": 4.8}
    normal_eval = FixedIncomeMacroEngine.evaluate_yield_curve(normal_rates)
    assert normal_eval["is_inverted"] is False
    assert normal_eval["recession_probability_indicator"] == "LOW"

    # Inverted curve (3M and 2Y higher than 10Y)
    inverted_rates = {"3M": 5.2, "2Y": 4.9, "5Y": 4.3, "10Y": 4.2, "30Y": 4.4}
    inverted_eval = FixedIncomeMacroEngine.evaluate_yield_curve(inverted_rates)
    assert inverted_eval["is_inverted"] is True
    assert "INVERTED" in inverted_eval["curve_regime"]
    assert inverted_eval["recession_probability_indicator"] == "HIGH"


# =============================================================================
# 4. CRYPTO DERIVATIVES ENGINE TESTS
# =============================================================================

def test_crypto_perpetual_funding_analytics():
    """Verify perpetual funding rate annualization and cascade risk scores."""
    r8 = 0.01  # 0.01% per 8h
    spot = 60000.0
    mark = 60060.0

    analytics = CryptoDerivativesEngine.perpetual_funding_analytics(r8, spot, mark)

    # Simple annualized: 0.01% * 3 * 365 = 10.95%
    assert pytest.approx(analytics["simple_annualized_pct"], abs=0.1) == 10.95
    assert "Longs Pay Shorts" in analytics["carry_direction"]
    assert analytics["premium_index_bps"] > 0


def test_crypto_liquidation_price_calculations():
    """Verify isolated margin liquidation prices under leverage."""
    entry = 50000.0
    leverage = 10.0  # 10x leverage
    maint_margin_rate = 0.005  # 0.5%

    long_liq = CryptoDerivativesEngine.liquidation_price(entry, leverage, "long", maint_margin_rate)
    short_liq = CryptoDerivativesEngine.liquidation_price(entry, leverage, "short", maint_margin_rate)

    # Long liquidation is below entry price (~10% down)
    assert long_liq["liquidation_price"] < entry
    assert pytest.approx(long_liq["adverse_buffer_pct"], abs=0.5) == 9.5

    # Short liquidation is above entry price (~10% up)
    assert short_liq["liquidation_price"] > entry
    assert pytest.approx(short_liq["adverse_buffer_pct"], abs=0.5) == 9.5


# =============================================================================
# 5. CROSS-ASSET RISK ENGINE TESTS
# =============================================================================

def test_parametric_var_and_cvar():
    """Verify Parametric VaR (95%/99%) and Expected Shortfall scaling."""
    portfolio_value = 1_000_000.0
    weights = {"equities": 0.60, "bonds": 0.40}
    vols = {"equities": 0.18, "bonds": 0.06}
    corr = {
        "equities": {"equities": 1.0, "bonds": 0.10},
        "bonds": {"equities": 0.10, "bonds": 1.0}
    }

    risk = CrossAssetRiskEngine.calculate_var_cvar(portfolio_value, weights, vols, corr, horizon_days=1)

    assert risk["portfolio_value"] == portfolio_value
    # 99% VaR must be strictly larger than 95% VaR
    assert risk["var_99_dollar"] > risk["var_95_dollar"]
    # CVaR (Expected Shortfall) must be strictly larger than VaR at same confidence
    assert risk["cvar_95_dollar"] > risk["var_95_dollar"]
    assert risk["cvar_99_dollar"] > risk["var_99_dollar"]


def test_crisis_stress_testing_scenarios():
    """Verify historical crisis scenarios (2008 GFC, 2020 COVID) calculate drawdowns."""
    allocations = {
        "equities": 600_000.0,
        "fixed_income": 300_000.0,
        "commodities": 50_000.0,
        "crypto": 50_000.0
    }

    stress = CrossAssetRiskEngine.simulate_crisis_stress(allocations)

    assert stress["total_portfolio_equity"] == 1_000_000.0
    assert len(stress["scenarios"]) == 4

    gfc = next(s for s in stress["scenarios"] if s["scenario_id"] == "2008_GFC_CRASH")
    assert gfc["projected_pnl_usd"] < 0
    assert gfc["surviving_equity_usd"] < 1_000_000.0
    assert gfc["severity"] in ["CRITICAL BREACH", "WARNING"]
