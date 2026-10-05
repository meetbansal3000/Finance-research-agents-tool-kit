"""
Unit tests for the Financial Calculation Toolkit (/tools/calc/)
All expected values are independently computed using standard analytical formulas.
"""

import pytest
import math
from tools.calc.metrics import (
    yoy_growth,
    cagr,
    margin,
    roic,
    roe,
    free_cash_flow,
    fcf_yield,
    net_debt_to_ebitda,
    interest_coverage,
    cash_conversion,
    enterprise_value,
    ev_multiples
)
from tools.calc.dcf import dcf, reverse_dcf
from tools.calc.fx import convert_currency

def test_yoy_growth():
    # Hand calculation: (115 - 100) / 100 = 0.15 = 15.0%
    expected = ((115.0 - 100.0) / 100.0) * 100.0
    res = yoy_growth(current_period=115.0, prior_period=100.0)
    assert pytest.approx(res["result"], rel=1e-6) == expected
    assert "+15.00%" in res["formatted"]
    
    # Negative growth: (80 - 100) / 100 = -20.0%
    expected_neg = ((80.0 - 100.0) / 100.0) * 100.0
    res_neg = yoy_growth(current_period=80.0, prior_period=100.0)
    assert pytest.approx(res_neg["result"], rel=1e-6) == expected_neg

def test_cagr():
    # Hand calculation: (200 / 100) ^ (1/4) - 1 = 2 ^ 0.25 - 1 = 18.9207115%
    expected = (math.pow(200.0 / 100.0, 1.0 / 4.0) - 1.0) * 100.0
    res = cagr(start_value=100.0, end_value=200.0, periods=4.0)
    assert pytest.approx(res["result"], rel=1e-6) == expected
    assert "18.92%" in res["formatted"]

def test_margins():
    # Hand calculation: 45 / 100 = 45.0%
    expected = (45.0 / 100.0) * 100.0
    res_gross = margin(numerator=45.0, revenue=100.0, margin_type="gross")
    assert pytest.approx(res_gross["result"], rel=1e-6) == expected
    assert "45.00%" in res_gross["formatted"]

def test_roic_and_roe():
    # Hand calculation: 18 / 120 = 15.0%
    expected_roic = (18.0 / 120.0) * 100.0
    res_roic = roic(nopat=18.0, invested_capital=120.0)
    assert pytest.approx(res_roic["result"], rel=1e-6) == expected_roic
    
    # Hand calculation: 25 / 100 = 25.0%
    expected_roe = (25.0 / 100.0) * 100.0
    res_roe = roe(net_income=25.0, shareholders_equity=100.0)
    assert pytest.approx(res_roe["result"], rel=1e-6) == expected_roe

def test_fcf_and_yield():
    # Hand calculation: 150 - 30 = 120.0
    expected_fcf = 150.0 - 30.0
    res_fcf = free_cash_flow(operating_cash_flow=150.0, capital_expenditures=30.0)
    assert pytest.approx(res_fcf["result"], rel=1e-6) == expected_fcf
    
    # Hand calculation: 120 / 2400 = 5.0%
    expected_yield = (expected_fcf / 2400.0) * 100.0
    res_yield = fcf_yield(free_cash_flow_val=expected_fcf, market_cap=2400.0)
    assert pytest.approx(res_yield["result"], rel=1e-6) == expected_yield

def test_debt_and_coverage():
    # Hand calculation: (100 - 20) / 40 = 2.0x
    expected_leverage = (100.0 - 20.0) / 40.0
    res_nd = net_debt_to_ebitda(total_debt=100.0, cash_and_equivalents=20.0, ebitda=40.0)
    assert pytest.approx(res_nd["result"], rel=1e-6) == expected_leverage
    
    # Hand calculation: 80 / 8 = 10.0x
    expected_cov = 80.0 / 8.0
    res_cov = interest_coverage(operating_income_or_ebit=80.0, interest_expense=8.0)
    assert pytest.approx(res_cov["result"], rel=1e-6) == expected_cov

def test_cash_conversion():
    # Hand calculation: 115 / 100 = 115.0%
    expected = (115.0 / 100.0) * 100.0
    res_cc = cash_conversion(operating_cash_flow=115.0, net_income=100.0)
    assert pytest.approx(res_cc["result"], rel=1e-6) == expected

def test_enterprise_value_and_multiples():
    # Hand calculation: 1000 + 250 - 50 = 1200.0
    expected_ev = 1000.0 + 250.0 - 50.0
    res_ev = enterprise_value(market_cap=1000.0, total_debt=250.0, cash_and_equivalents=50.0)
    assert pytest.approx(res_ev["result"], rel=1e-6) == expected_ev
    
    # Hand calculation: 1200 / 120 = 10.0x, 1200 / 600 = 2.0x, 1200 / 100 = 12.0x
    res_mult = ev_multiples(ev=expected_ev, ebitda=120.0, revenue=600.0, ebit=100.0)
    assert pytest.approx(res_mult["result"]["ev_ebitda"], rel=1e-6) == expected_ev / 120.0
    assert pytest.approx(res_mult["result"]["ev_sales"], rel=1e-6) == expected_ev / 600.0
    assert pytest.approx(res_mult["result"]["ev_ebit"], rel=1e-6) == expected_ev / 100.0

def test_dcf_analytical():
    # Hand-worked analytical DCF:
    # FCF0 = 100, g = 8% for 5 years, r = 10%, g_term = 2.5%, shares = 1.0, debt = 0
    # PV = sum_{i=1..5} [100*(1.08)^i / (1.10)^i] + [100*(1.08)^5*(1.025)/(0.10-0.025)] / (1.10)^5
    explicit_pv = sum((100.0 * (1.08 ** i)) / (1.10 ** i) for i in range(1, 6))
    terminal_fcf = 100.0 * (1.08 ** 5) * 1.025
    terminal_val = terminal_fcf / (0.10 - 0.025)
    pv_terminal_val = terminal_val / (1.10 ** 5)
    expected_total_ev = explicit_pv + pv_terminal_val
    expected_per_share = expected_total_ev / 1.0

    res = dcf(
        base_fcf=100.0,
        growth_rates=[0.08] * 5,
        discount_rate=0.10,
        terminal_growth_rate=0.025,
        shares_outstanding=1.0,
        net_debt=0.0
    )
    assert pytest.approx(res["result"]["enterprise_value"], rel=1e-5) == expected_total_ev
    assert pytest.approx(res["result"]["fair_value_per_share"], rel=1e-5) == expected_per_share

def test_reverse_dcf_analytical():
    # Given the exact analytical fair value per share from test_dcf_analytical, reverse DCF must recover 8.0%
    explicit_pv = sum((100.0 * (1.08 ** i)) / (1.10 ** i) for i in range(1, 6))
    terminal_val = (100.0 * (1.08 ** 5) * 1.025) / (0.10 - 0.025)
    target_price = (explicit_pv + terminal_val / (1.10 ** 5)) / 1.0

    res_rev = reverse_dcf(
        current_price=target_price,
        base_fcf=100.0,
        shares_outstanding=1.0,
        discount_rate=0.10,
        terminal_growth_rate=0.025,
        projection_years=5,
        net_debt=0.0
    )
    assert pytest.approx(res_rev["result"]["implied_growth_rate_pct"], abs=1e-3) == 8.0

def test_currency_conversion():
    # Hand calculation: 1000 * 0.92 = 920.0
    res = convert_currency(amount=1000.0, from_currency="USD", to_currency="EUR", custom_rate=0.92, rate_date="2026-10-05")
    assert pytest.approx(res["result"], rel=1e-6) == 920.0
    assert res["rate"] == 0.92
    assert res["rate_date"] == "2026-10-05"
    assert "source" in res
