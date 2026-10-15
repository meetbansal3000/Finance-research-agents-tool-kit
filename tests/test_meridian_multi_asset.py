"""
tests/test_meridian_multi_asset.py
Comprehensive test suite for Meridian Multi-Asset Master Orchestrator and 5 specialized desks:
1. Options Greek Strategist
2. Futures & Commodity Desk Agent
3. Fixed Income Macro Agent
4. Crypto & 24/7 Derivatives Agent
5. Cross-Asset Risk Officer
6. Meridian Multi-Asset Master Orchestrator End-to-End
"""

import pytest
import math
from tools.ledger import ProvenanceLedger
from tools.calc.derivatives_math import (
    BlackScholesEngine,
    FuturesCommodityEngine,
    FixedIncomeMacroEngine,
    CryptoDerivativesEngine,
    CrossAssetRiskEngine
)
from agents.options_greek_agent import OptionsGreekStrategist
from agents.futures_commodity_agent import FuturesCommodityAgent
from agents.fixed_income_macro_agent import FixedIncomeMacroAgent
from agents.crypto_derivatives_agent import CryptoDerivativesAgent
from agents.cross_asset_risk_officer import CrossAssetRiskOfficer
from agents.meridian_orchestrator import MeridianMultiAssetOrchestrator


# =============================================================================
# 1. MATHEMATICAL DERIVATIVES & RISK ENGINES
# =============================================================================

def test_black_scholes_pricing_and_greeks():
    # Benchmark European Call: Spot=100, Strike=100, T=1.0, r=0.05, vol=0.20
    call_res = BlackScholesEngine.price_and_greeks(
        spot=100.0, strike=100.0, time_to_expiry=1.0, risk_free_rate=0.05, volatility=0.20, option_type="call"
    )
    # Theoretical BSM Call Price approx 10.4506
    assert abs(call_res["price"] - 10.4506) < 0.05
    assert 0.50 < call_res["delta"] < 0.70
    assert call_res["gamma"] > 0
    assert call_res["vega"] > 0
    assert call_res["theta_daily"] < 0  # Time decay is negative
    assert call_res["rho"] > 0
    assert "vanna" in call_res
    assert "volga" in call_res
    assert "charm" in call_res

    # Benchmark European Put: Put-Call Parity: C - P = S - K*exp(-r*T)
    put_res = BlackScholesEngine.price_and_greeks(
        spot=100.0, strike=100.0, time_to_expiry=1.0, risk_free_rate=0.05, volatility=0.20, option_type="put"
    )
    # Theoretical BSM Put Price approx 5.5735
    assert abs(put_res["price"] - 5.5735) < 0.05
    assert -0.50 < put_res["delta"] < 0.0
    assert put_res["gamma"] == call_res["gamma"]  # Gamma is identical for calls & puts

    # Put-Call Parity validation: C - P approx 100 - 100*exp(-0.05) = 4.877
    parity_diff = (call_res["price"] - put_res["price"]) - (100.0 - 100.0 * math.exp(-0.05))
    assert abs(parity_diff) < 0.01


def test_black_scholes_implied_volatility():
    known_vol = 0.285
    call_res = BlackScholesEngine.price_and_greeks(
        spot=150.0, strike=155.0, time_to_expiry=0.5, risk_free_rate=0.04, volatility=known_vol, option_type="call"
    )
    mkt_px = call_res["price"]
    solved_iv = BlackScholesEngine.implied_volatility(
        market_price=mkt_px, spot=150.0, strike=155.0, time_to_expiry=0.5, risk_free_rate=0.04, option_type="call"
    )
    assert abs(solved_iv - known_vol) < 0.001


def test_options_strategy_legs():
    # Long Straddle: Long 1 Call + Long 1 Put at the money
    legs = [
        {"type": "call", "strike": 100.0, "quantity": 1, "volatility": 0.20, "expiry_years": 0.25},
        {"type": "put", "strike": 100.0, "quantity": 1, "volatility": 0.20, "expiry_years": 0.25}
    ]
    strat = BlackScholesEngine.analyze_strategy_legs(spot=100.0, legs=legs, risk_free_rate=0.05)
    assert strat["structure"] == "Debit"
    assert strat["net_debit_credit"] > 0
    assert abs(strat["net_delta"]) < 0.2  # Near delta-neutral
    assert strat["net_gamma"] > 0
    assert strat["net_vega"] > 0
    assert len(strat["breakevens"]) == 2  # Lower and upper breakeven


def test_futures_commodity_cost_of_carry():
    # Spot=70, r=0.05, storage=0.02, conv_yield=0.01 -> net carry = 0.06
    res = FuturesCommodityEngine.theoretical_futures_price(
        spot=70.0, time_to_expiry_years=1.0, risk_free_rate=0.05, storage_cost_annual=0.02, convenience_yield_annual=0.01
    )
    expected_f = 70.0 * math.exp(0.06)
    assert abs(res["theoretical_futures_price"] - expected_f) < 0.01
    assert res["regime"] == "Contango"
    assert res["net_cost_of_carry_annual_pct"] == 6.0


def test_futures_term_structure_roll_yield():
    # Contango curve
    contango_curve = [
        {"contract": "M1", "days_to_expiry": 30, "price": 70.0},
        {"contract": "M2", "days_to_expiry": 60, "price": 71.5},
        {"contract": "M6", "days_to_expiry": 180, "price": 75.0}
    ]
    c_res = FuturesCommodityEngine.analyze_term_structure(contango_curve)
    assert c_res["is_contango"] is True
    assert c_res["front_to_deferred_roll_yield_annual_pct"] < 0  # Negative roll yield for longs

    # Backwardation curve
    back_curve = [
        {"contract": "M1", "days_to_expiry": 30, "price": 85.0},
        {"contract": "M2", "days_to_expiry": 60, "price": 82.0},
        {"contract": "M6", "days_to_expiry": 180, "price": 76.0}
    ]
    b_res = FuturesCommodityEngine.analyze_term_structure(back_curve)
    assert b_res["is_contango"] is False
    assert b_res["front_to_deferred_roll_yield_annual_pct"] > 0  # Positive roll yield for longs


def test_futures_margin_and_leverage():
    res = FuturesCommodityEngine.calculate_margin_buffer(
        contract_multiplier=1000.0,
        futures_price=75.0,
        num_contracts=10,
        initial_margin_per_contract=6000.0,
        maintenance_margin_per_contract=4500.0,
        account_equity=100000.0
    )
    assert res["total_notional"] == 750000.0
    assert res["effective_leverage"] == 7.5
    assert res["margin_utilization_pct"] == 60.0
    assert res["free_margin_headroom"] == 55000.0
    assert res["margin_call_trigger_price"] < 75.0


def test_fixed_income_bond_duration_and_dv01():
    # 10Y Par bond (coupon = YTM = 5%)
    res = FixedIncomeMacroEngine.bond_sensitivities(
        face_value=1000.0, coupon_rate_annual=0.05, yield_to_maturity_annual=0.05, years_to_maturity=10.0
    )
    assert abs(res["price"] - 1000.0) < 0.01  # Par bond prices at par
    assert 7.0 < res["modified_duration"] < 8.5
    assert res["convexity"] > 0
    assert res["dv01_per_million_par"] > 700.0  # Approx $700-$800 per 1 bp on $1M
    assert "+100bps" in res["rate_shocks"]
    assert res["rate_shocks"]["+100bps"]["pct_change"] < 0  # Yield up -> price down


def test_fixed_income_yield_curve_regime():
    # Inverted curve (2Y > 10Y)
    inv_rates = {"3M": 5.20, "2Y": 4.80, "5Y": 4.30, "10Y": 4.10, "30Y": 4.40}
    inv_res = FixedIncomeMacroEngine.evaluate_yield_curve(inv_rates)
    assert inv_res["is_inverted"] is True
    assert inv_res["spread_2y_10y_bps"] == -70.0
    assert "INVERTED" in inv_res["curve_regime"]
    assert inv_res["recession_probability_indicator"] == "HIGH"


def test_crypto_perpetual_funding():
    # 8h rate = +0.01% -> annual approx +10.95%
    res = CryptoDerivativesEngine.perpetual_funding_analytics(
        funding_rate_8h_pct=0.01, spot_price=60000.0, mark_price=60030.0
    )
    assert abs(res["simple_annualized_pct"] - 10.95) < 0.1
    assert "Longs Pay Shorts" in res["carry_direction"]
    assert 0 <= res["liquidation_cascade_risk_score"] <= 100


def test_crypto_cash_and_carry_basis():
    res = CryptoDerivativesEngine.cash_and_carry_basis(
        spot_price=60000.0, futures_price=61800.0, days_to_expiry=90
    )
    # Basis = 1800 / 60000 = 3.0% in 90 days -> approx 12.17% annualized
    assert res["gross_basis_pct"] == 3.0
    assert res["gross_annualized_apy_pct"] > 11.5
    assert res["arbitrage_viable"] is True


def test_crypto_liquidation_price():
    # Long at $60,000 with 10x leverage, 0.5% maint margin -> liq price approx $54,300
    res = CryptoDerivativesEngine.liquidation_price(
        entry_price=60000.0, leverage=10.0, position_side="long", maintenance_margin_rate=0.005
    )
    assert 54000.0 < res["liquidation_price"] < 55000.0
    assert abs(res["adverse_buffer_pct"] - 9.5) < 0.2


def test_cross_asset_var_and_cvar():
    allocations = {"equities": 0.5, "fixed_income": 0.5}
    vols = {"equities": 0.20, "fixed_income": 0.06}
    corrs = {"equities": {"equities": 1.0, "fixed_income": 0.0}, "fixed_income": {"equities": 0.0, "fixed_income": 1.0}}

    var_res = CrossAssetRiskEngine.calculate_var_cvar(
        portfolio_value=1_000_000.0, asset_weights=allocations, asset_volatilities_annual=vols, correlation_matrix=corrs, horizon_days=1
    )
    assert var_res["var_95_pct"] > 0
    assert var_res["var_99_pct"] > var_res["var_95_pct"]
    assert abs(var_res["var_99_dollar"] - 1_000_000.0 * (var_res["var_99_pct"] / 100.0)) < 1.0


def test_cross_asset_crisis_stress():
    allocations = {"equities": 6_000_000.0, "fixed_income": 4_000_000.0}
    stress_res = CrossAssetRiskEngine.simulate_crisis_stress(allocations)
    assert len(stress_res["scenarios"]) >= 4
    for s in stress_res["scenarios"]:
        assert "projected_drawdown_pct" in s
        assert "projected_pnl_usd" in s


# =============================================================================
# 2. SPECIALIZED DESK AGENTS
# =============================================================================

def test_options_greek_agent_contract_and_strategy():
    ledger = ProvenanceLedger(run_id="test_opt_ledger")
    agent = OptionsGreekStrategist(ledger=ledger)

    # 1. Single contract
    res = agent.analyze_contract(
        underlying_ticker="AAPL", spot_price=220.0, strike_price=230.0, time_to_expiry_years=30/365.0, volatility=0.22, option_type="call"
    )
    assert res["agent"] == "Options Greek Strategist"
    assert res["provenance_ledger_id"].startswith("LEDGER_")
    assert res["provenance_ledger_id"] in ledger.entries

    # 2. Near-expiry gamma cliff detection
    cliff_res = agent.analyze_contract(
        underlying_ticker="TSLA", spot_price=250.0, strike_price=250.0, time_to_expiry_years=2/365.0, volatility=0.60, option_type="call"
    )
    cliff_flags = [f for f in cliff_res["red_flags"] if f["category"] == "Gamma Cliff Risk"]
    assert len(cliff_flags) >= 1

    # 3. Strategy evaluation
    legs = [
        {"type": "call", "strike": 220.0, "quantity": 1, "volatility": 0.22, "expiry_years": 0.1},
        {"type": "call", "strike": 235.0, "quantity": -1, "volatility": 0.22, "expiry_years": 0.1}
    ]
    strat_res = agent.evaluate_strategy("Bull Call Spread", "AAPL", 220.0, legs)
    assert strat_res["verdict"] == "APPROVED"


def test_futures_commodity_agent_analysis_and_red_flags():
    ledger = ProvenanceLedger(run_id="test_fut_ledger")
    agent = FuturesCommodityAgent(ledger=ledger)

    # Contango curve with > 10% roll decay
    curve = [
        {"contract": "CL1", "days_to_expiry": 20, "price": 70.0},
        {"contract": "CL2", "days_to_expiry": 50, "price": 72.5},
        {"contract": "CL6", "days_to_expiry": 170, "price": 80.0}
    ]
    ts_res = agent.evaluate_term_structure("CL", "WTI Crude Oil", curve)
    assert ts_res["term_structure"]["is_contango"] is True
    # Should trigger Severe Contango Roll Decay red flag
    decay_flags = [f for f in ts_res["red_flags"] if "Contango" in f["category"]]
    assert len(decay_flags) >= 1

    # Hyper-leverage check
    margin_res = agent.assess_margin_and_leverage(
        symbol="CL", futures_price=70.0, contract_multiplier=1000.0, num_contracts=25,
        initial_margin_per_contract=6000.0, maintenance_margin_per_contract=5000.0, account_equity=100000.0
    )
    assert margin_res["verdict"] == "REJECTED"  # Leverage 17.5x exceeds 10x cap
    assert any(f["severity"] == "CRITICAL" for f in margin_res["red_flags"])


def test_fixed_income_macro_agent():
    ledger = ProvenanceLedger(run_id="test_fi_ledger")
    agent = FixedIncomeMacroAgent(ledger=ledger)

    # Inverted curve check
    rates = {"3M": 5.10, "2Y": 4.60, "5Y": 4.10, "10Y": 3.90, "30Y": 4.25}
    res = agent.evaluate_yield_curve_macro(rates)
    assert res["yield_curve_analysis"]["is_inverted"] is True
    assert any("Inversion" in f["category"] for f in res["red_flags"])
    assert res["portfolio_duration_recommendation"] == "UNDERWEIGHT_DURATION"


def test_crypto_derivatives_agent():
    ledger = ProvenanceLedger(run_id="test_cr_ledger")
    agent = CryptoDerivativesAgent(ledger=ledger)

    # Normal perp funding
    res = agent.analyze_perpetual_funding(
        symbol="BTC-PERP", spot_price=64000.0, mark_price=64050.0, funding_rate_8h_pct=0.01
    )
    assert res["agent"] == "Crypto & 24/7 Derivatives Agent"
    assert res["provenance_ledger_id"] in ledger.entries

    # Reckless leverage check
    liq_res = agent.evaluate_liquidation_buffer(
        symbol="BTC-PERP", entry_price=64000.0, leverage=25.0
    )
    assert liq_res["verdict"] == "REJECTED"
    assert any(f["category"] == "Reckless 24/7 Crypto Leverage" for f in liq_res["red_flags"])


def test_cross_asset_risk_officer():
    ledger = ProvenanceLedger(run_id="test_risk_ledger")
    officer = CrossAssetRiskOfficer(ledger=ledger)

    allocations = {
        "equities": 4_000_000.0,
        "fixed_income": 4_000_000.0,
        "commodities": 1_000_000.0,
        "crypto": 1_000_000.0
    }
    var_res = officer.evaluate_portfolio_var(portfolio_value_usd=10_000_000.0, allocations_usd=allocations)
    assert var_res["provenance_ledger_id"] in ledger.entries

    # Consolidated audit
    desk_reports = {
        "Options Desk": {"red_flags": []},
        "Futures Desk": {"red_flags": [{"severity": "MEDIUM", "category": "Basis Notice", "message": "Basis tight."}]}
    }
    audit = officer.consolidate_risk_audit(portfolio_summary={"red_flags": []}, desk_reports=desk_reports)
    assert audit["verdict"] == "APPROVED"
    assert audit["total_red_flags"] == 1


# =============================================================================
# 3. MERIDIAN MASTER ORCHESTRATOR END-TO-END
# =============================================================================

def test_meridian_master_orchestrator_full_workflow():
    ledger = ProvenanceLedger(run_id="test_meridian_full")
    orchestrator = MeridianMultiAssetOrchestrator(ledger=ledger)

    allocations = {
        "equities": 4_000_000.0,
        "fixed_income": 3_500_000.0,
        "commodities": 1_500_000.0,
        "crypto": 500_000.0,
        "options_overlay": 500_000.0
    }

    result = orchestrator.run_multi_asset_committee(
        portfolio_name="Alpha Global Macro Fund",
        total_capital_usd=10_000_000.0,
        allocations_usd=allocations
    )

    assert result["orchestrator"] == "MERIDIAN MULTI-ASSET MASTER ORCHESTRATOR"
    assert result["portfolio_name"] == "Alpha Global Macro Fund"
    assert result["total_capital_usd"] == 10_000_000.0
    assert result["risk_verdict"] in ("APPROVED", "CONDITIONAL_APPROVAL", "REJECTED")
    assert result["master_ledger_id"].startswith("LEDGER_")
    assert result["master_ledger_id"] in ledger.entries

    # Verify all 5 desk reports are present
    desks = result["desk_reports"]
    assert "Options Greek Strategist" in desks
    assert "Futures & Commodity Desk" in desks
    assert "Fixed Income Macro Agent" in desks
    assert "Crypto & 24/7 Derivatives Agent" in desks
    assert "Cross-Asset Risk Officer" in desks

    # Verify Red Flags register exists and is populated
    assert isinstance(result["red_flags_register"], list)
    assert result["total_red_flags"] == len(result["red_flags_register"])

    # Verify VaR and stress matrix
    assert "var_99_dollar" in result["var_metrics"]
    assert len(result["stress_matrix"]) >= 4
