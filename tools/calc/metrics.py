"""
Calculation Toolkit: Financial Metrics & Valuation Ratios
Each function returns a dictionary containing:
- result: The numeric calculated output (float)
- formula: String representation of the mathematical formula applied
- inputs: Dictionary of the raw input parameters used in the calculation
- formatted: Human-readable string with units and precision
"""

from typing import Dict, Any, List, Optional
import math

def yoy_growth(current_period: float, prior_period: float) -> Dict[str, Any]:
    """Calculate Year-over-Year (YoY) Growth Rate.
    Formula: ((current_period - prior_period) / prior_period) * 100
    """
    if prior_period == 0:
        raise ZeroDivisionError("Prior period value cannot be zero for growth calculation.")
    growth = ((current_period - prior_period) / abs(prior_period)) * 100.0
    return {
        "result": growth,
        "formula": "((current_period - prior_period) / abs(prior_period)) * 100",
        "inputs": {"current_period": current_period, "prior_period": prior_period},
        "formatted": f"{growth:+.2f}%"
    }

def cagr(start_value: float, end_value: float, periods: float) -> Dict[str, Any]:
    """Calculate Compound Annual Growth Rate (CAGR).
    Formula: ((end_value / start_value) ** (1 / periods) - 1) * 100
    """
    if start_value <= 0:
        raise ValueError("Start value must be strictly positive for CAGR calculation.")
    if periods <= 0:
        raise ValueError("Number of periods must be greater than zero.")
    if end_value < 0:
        raise ValueError("End value cannot be negative for CAGR calculation.")
    
    rate = ((end_value / start_value) ** (1.0 / periods) - 1.0) * 100.0
    return {
        "result": rate,
        "formula": "((end_value / start_value) ** (1 / periods) - 1) * 100",
        "inputs": {"start_value": start_value, "end_value": end_value, "periods": periods},
        "formatted": f"{rate:+.2f}%"
    }

def margin(numerator: float, revenue: float, margin_type: str = "margin") -> Dict[str, Any]:
    """Calculate Profit Margin (Gross, Operating, Net, etc.).
    Formula: (numerator / revenue) * 100
    """
    if revenue == 0:
        raise ZeroDivisionError("Revenue cannot be zero for margin calculation.")
    m = (numerator / revenue) * 100.0
    return {
        "result": m,
        "formula": f"({margin_type}_numerator / revenue) * 100",
        "inputs": {"numerator": numerator, "revenue": revenue, "margin_type": margin_type},
        "formatted": f"{m:.2f}%"
    }

def roic(nopat: float, invested_capital: float) -> Dict[str, Any]:
    """Calculate Return on Invested Capital (ROIC).
    Formula: (NOPAT / Invested Capital) * 100
    Where NOPAT = Operating Income * (1 - Effective Tax Rate)
    Invested Capital = Total Debt + Total Equity - Non-operating Cash
    """
    if invested_capital == 0:
        raise ZeroDivisionError("Invested capital cannot be zero.")
    roic_val = (nopat / invested_capital) * 100.0
    return {
        "result": roic_val,
        "formula": "(NOPAT / Invested Capital) * 100",
        "inputs": {"nopat": nopat, "invested_capital": invested_capital},
        "formatted": f"{roic_val:.2f}%"
    }

def roe(net_income: float, shareholders_equity: float) -> Dict[str, Any]:
    """Calculate Return on Equity (ROE).
    Formula: (Net Income / Shareholders' Equity) * 100
    """
    if shareholders_equity == 0:
        raise ZeroDivisionError("Shareholders' equity cannot be zero.")
    roe_val = (net_income / shareholders_equity) * 100.0
    return {
        "result": roe_val,
        "formula": "(Net Income / Shareholders' Equity) * 100",
        "inputs": {"net_income": net_income, "shareholders_equity": shareholders_equity},
        "formatted": f"{roe_val:.2f}%"
    }

def free_cash_flow(operating_cash_flow: float, capital_expenditures: float) -> Dict[str, Any]:
    """Calculate Free Cash Flow (FCF).
    Formula: Operating Cash Flow (CFO) - Capital Expenditures (CapEx)
    """
    fcf = operating_cash_flow - capital_expenditures
    return {
        "result": fcf,
        "formula": "Operating Cash Flow - Capital Expenditures",
        "inputs": {"operating_cash_flow": operating_cash_flow, "capital_expenditures": capital_expenditures},
        "formatted": f"{fcf:,.2f}"
    }

def fcf_yield(free_cash_flow_val: float, market_cap: float) -> Dict[str, Any]:
    """Calculate Free Cash Flow Yield.
    Formula: (Free Cash Flow / Market Capitalization) * 100
    """
    if market_cap == 0:
        raise ZeroDivisionError("Market cap cannot be zero.")
    yield_pct = (free_cash_flow_val / market_cap) * 100.0
    return {
        "result": yield_pct,
        "formula": "(Free Cash Flow / Market Capitalization) * 100",
        "inputs": {"free_cash_flow": free_cash_flow_val, "market_cap": market_cap},
        "formatted": f"{yield_pct:.2f}%"
    }

def net_debt_to_ebitda(total_debt: float, cash_and_equivalents: float, ebitda: float) -> Dict[str, Any]:
    """Calculate Net Debt to EBITDA ratio.
    Formula: (Total Debt - Cash & Equivalents) / EBITDA
    """
    if ebitda == 0:
        raise ZeroDivisionError("EBITDA cannot be zero.")
    net_debt = total_debt - cash_and_equivalents
    ratio = net_debt / ebitda
    return {
        "result": ratio,
        "formula": "(Total Debt - Cash & Equivalents) / EBITDA",
        "inputs": {
            "total_debt": total_debt,
            "cash_and_equivalents": cash_and_equivalents,
            "net_debt": net_debt,
            "ebitda": ebitda
        },
        "formatted": f"{ratio:.2f}x (Net Debt: {net_debt:,.2f})"
    }

def interest_coverage(operating_income_or_ebit: float, interest_expense: float) -> Dict[str, Any]:
    """Calculate Interest Coverage Ratio.
    Formula: EBIT / Interest Expense
    """
    if interest_expense == 0:
        return {
            "result": float("inf"),
            "formula": "EBIT / Interest Expense",
            "inputs": {"ebit": operating_income_or_ebit, "interest_expense": interest_expense},
            "formatted": "Infinity (Zero interest expense)"
        }
    cover = operating_income_or_ebit / abs(interest_expense)
    return {
        "result": cover,
        "formula": "EBIT / abs(Interest Expense)",
        "inputs": {"ebit": operating_income_or_ebit, "interest_expense": interest_expense},
        "formatted": f"{cover:.2f}x"
    }

def cash_conversion(operating_cash_flow: float, net_income: float) -> Dict[str, Any]:
    """Calculate Cash Conversion Ratio.
    Formula: (Operating Cash Flow / Net Income) * 100
    """
    if net_income == 0:
        raise ZeroDivisionError("Net income cannot be zero.")
    conv = (operating_cash_flow / net_income) * 100.0
    return {
        "result": conv,
        "formula": "(Operating Cash Flow / Net Income) * 100",
        "inputs": {"operating_cash_flow": operating_cash_flow, "net_income": net_income},
        "formatted": f"{conv:.2f}%"
    }

def enterprise_value(
    market_cap: float,
    total_debt: float,
    cash_and_equivalents: float,
    preferred_stock: float = 0.0,
    minority_interest: float = 0.0
) -> Dict[str, Any]:
    """Calculate Enterprise Value (EV).
    Formula: Market Cap + Total Debt + Preferred Stock + Minority Interest - Cash & Equivalents
    """
    ev = market_cap + total_debt + preferred_stock + minority_interest - cash_and_equivalents
    return {
        "result": ev,
        "formula": "Market Cap + Total Debt + Preferred Stock + Minority Interest - Cash & Equivalents",
        "inputs": {
            "market_cap": market_cap,
            "total_debt": total_debt,
            "cash_and_equivalents": cash_and_equivalents,
            "preferred_stock": preferred_stock,
            "minority_interest": minority_interest
        },
        "formatted": f"{ev:,.2f}"
    }

def ev_multiples(ev: float, ebitda: Optional[float] = None, revenue: Optional[float] = None, ebit: Optional[float] = None) -> Dict[str, Any]:
    """Calculate EV/EBITDA, EV/Sales, and EV/EBIT multiples."""
    res = {}
    if ebitda and ebitda > 0:
        res["ev_ebitda"] = ev / ebitda
    if revenue and revenue > 0:
        res["ev_sales"] = ev / revenue
    if ebit and ebit > 0:
        res["ev_ebit"] = ev / ebit
        
    return {
        "result": res,
        "formula": "EV / Metric (EBITDA, Revenue, or EBIT)",
        "inputs": {"ev": ev, "ebitda": ebitda, "revenue": revenue, "ebit": ebit},
        "formatted": ", ".join(f"{k.upper()}: {v:.2f}x" for k, v in res.items())
    }
