"""
Unit tests for the Financial Calculation Toolkit (/tools/calc/)
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
    res = yoy_growth(current_period=115.0, prior_period=100.0)
    assert pytest.approx(res["result"], rel=1e-4) == 15.0
    assert "formula" in res
    assert "inputs" in res
    assert "+15.00%" in res["formatted"]
    
    # Negative growth
    res_neg = yoy_growth(current_period=80.0, prior_period=100.0)
    assert pytest.approx(res_neg["result"], rel=1e-4) == -20.0

def test_cagr():
    # 100 growing to 200 in 4 years: (200/100)^(1/4) - 1 = 18.9207%
    res = cagr(start_value=100.0, end_value=200.0, periods=4)
    expected = ((200.0 / 100.0) ** (1.0 / 4.0) - 1.0) * 100.0
    assert pytest.approx(res["result"], rel=1e-4) == expected
    assert "18.92%" in res["formatted"]

def test_margins():
    res_gross = margin(numerator=45.0, revenue=100.0, margin_type="gross")
    assert pytest.approx(res_gross["result"], rel=1e-4) == 45.0
    assert "45.00%" in res_gross["formatted"]

def test_roic_and_roe():
    res_roic = roic(nopat=18.0, invested_capital=120.0)
    assert pytest.approx(res_roic["result"], rel=1e-4) == 15.0
    
    res_roe = roe(net_income=25.0, shareholders_equity=100.0)
    assert pytest.approx(res_roe["result"], rel=1e-4) == 25.0

def test_fcf_and_yield():
    res_fcf = free_cash_flow(operating_cash_flow=150.0, capital_expenditures=30.0)
    assert pytest.approx(res_fcf["result"], rel=1e-4) == 120.0
    
    res_yield = fcf_yield(free_cash_flow_val=120.0, market_cap=2400.0)
    assert pytest.approx(res_yield["result"], rel=1e-4) == 5.0

def test_debt_and_coverage():
    res_nd = net_debt_to_ebitda(total_debt=100.0, cash_and_equivalents=20.0, ebitda=40.0)
    # Net Debt = 80, EBITDA = 40 -> 2.0x
    assert pytest.approx(res_nd["result"], rel=1e-4) == 2.0
    
    res_cov = interest_coverage(operating_income_or_ebit=80.0, interest_expense=8.0)
    assert pytest.approx(res_cov["result"], rel=1e-4) == 10.0

def test_cash_conversion():
    res_cc = cash_conversion(operating_cash_flow=115.0, net_income=100.0)
    assert pytest.approx(res_cc["result"], rel=1e-4) == 115.0

def test_enterprise_value_and_multiples():
    res_ev = enterprise_value(market_cap=1000.0, total_debt=250.0, cash_and_equivalents=50.0)
    assert pytest.approx(res_ev["result"], rel=1e-4) == 1200.0
    
    res_mult = ev_multiples(ev=1200.0, ebitda=120.0, revenue=600.0, ebit=100.0)
    assert pytest.approx(res_mult["result"]["ev_ebitda"], rel=1e-4) == 10.0
    assert pytest.approx(res_mult["result"]["ev_sales"], rel=1e-4) == 2.0
    assert pytest.approx(res_mult["result"]["ev_ebit"], rel=1e-4) == 12.0

def test_dcf():
    # Base FCF = 100, constant growth 5% for 3 years, discount rate 10%, terminal growth 3%, 10 shares
    growth_rates = [0.05, 0.05, 0.05]
    res_dcf = dcf(
        base_fcf=100.0,
        growth_rates=growth_rates,
        discount_rate=0.10,
        terminal_growth_rate=0.03,
        shares_outstanding=10.0,
        net_debt=0.0
    )
    
    # Year 1: 105 / 1.10 = 95.4545
    # Year 2: 110.25 / 1.21 = 91.1157
    # Year 3: 115.7625 / 1.331 = 86.9741
    # PV explicit = 273.5443
    # Terminal Value = (115.7625 * 1.03) / (0.10 - 0.03) = 119.235375 / 0.07 = 1703.3625
    # PV Terminal Value = 1703.3625 / 1.331 = 1279.7615
    # Total Enterprise Value = 273.5443 + 1279.7615 = 1553.3058
    # Fair Value per share = 155.33
    fv = res_dcf["result"]["fair_value_per_share"]
    assert pytest.approx(fv, rel=1e-2) == 155.33

def test_reverse_dcf():
    # When market price is 155.33 with 10 shares, reverse DCF should solve back to ~5.0% growth rate
    res_rev = reverse_dcf(
        current_price=155.33,
        base_fcf=100.0,
        shares_outstanding=10.0,
        discount_rate=0.10,
        terminal_growth_rate=0.03,
        projection_years=3,
        net_debt=0.0
    )
    implied_g = res_rev["result"]["implied_growth_rate_pct"]
    assert pytest.approx(implied_g, abs=0.1) == 5.0

def test_currency_conversion():
    res = convert_currency(amount=1000.0, from_currency="USD", to_currency="EUR", custom_rate=0.92, rate_date="2026-10-05")
    assert pytest.approx(res["result"], rel=1e-4) == 920.0
    assert res["rate"] == 0.92
    assert "2026-10-05" in res["rate_date"]
