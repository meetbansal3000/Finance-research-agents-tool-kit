"""
Calculation Toolkit: DCF & Reverse DCF Modeling
"""

from typing import Dict, Any, List, Optional
import math

def dcf(
    base_fcf: float,
    growth_rates: List[float],
    discount_rate: float,
    terminal_growth_rate: float,
    shares_outstanding: float,
    net_debt: float = 0.0
) -> Dict[str, Any]:
    """Calculate Discounted Cash Flow (DCF) Enterprise & Equity Value per share.
    
    Args:
        base_fcf: Most recent fiscal year Free Cash Flow.
        growth_rates: List of expected annual FCF growth rates (e.g., [0.12, 0.10, 0.08, 0.06, 0.05] for 12%, 10%, etc.).
        discount_rate: WACC or hurdle rate (e.g., 0.09 for 9.0%).
        terminal_growth_rate: Perpetual terminal growth rate (e.g., 0.025 for 2.5%). Must be < discount_rate.
        shares_outstanding: Diluted share count.
        net_debt: Total Debt - Cash & Equivalents.
    """
    if discount_rate <= terminal_growth_rate:
        raise ValueError("Discount rate must be strictly greater than terminal growth rate.")
    if shares_outstanding <= 0:
        raise ValueError("Shares outstanding must be positive.")
    
    projected_fcf = []
    pv_fcf = []
    current_fcf = base_fcf
    
    for i, g in enumerate(growth_rates, start=1):
        current_fcf = current_fcf * (1.0 + g)
        discount_factor = (1.0 + discount_rate) ** i
        pv = current_fcf / discount_factor
        projected_fcf.append(current_fcf)
        pv_fcf.append(pv)
        
    n_years = len(growth_rates)
    terminal_fcf = projected_fcf[-1] * (1.0 + terminal_growth_rate)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
    pv_terminal_value = terminal_value / ((1.0 + discount_rate) ** n_years)
    
    pv_explicit_cf = sum(pv_fcf)
    enterprise_value = pv_explicit_cf + pv_terminal_value
    equity_value = enterprise_value - net_debt
    fair_value_per_share = equity_value / shares_outstanding
    
    return {
        "result": {
            "fair_value_per_share": fair_value_per_share,
            "equity_value": equity_value,
            "enterprise_value": enterprise_value,
            "pv_explicit_fcf": pv_explicit_cf,
            "pv_terminal_value": pv_terminal_value,
            "terminal_value": terminal_value,
            "projected_fcf": projected_fcf
        },
        "formula": "Equity Value = Sum(PV of FCF) + PV(Terminal Value) - Net Debt; Fair Value = Equity Value / Shares",
        "inputs": {
            "base_fcf": base_fcf,
            "growth_rates": growth_rates,
            "discount_rate": discount_rate,
            "terminal_growth_rate": terminal_growth_rate,
            "shares_outstanding": shares_outstanding,
            "net_debt": net_debt
        },
        "formatted": f"Fair Value: ${fair_value_per_share:.2f}/share (Equity Val: ${equity_value:,.2f}, EV: ${enterprise_value:,.2f})"
    }

def reverse_dcf(
    current_price: float,
    base_fcf: float,
    shares_outstanding: float,
    discount_rate: float,
    terminal_growth_rate: float,
    projection_years: int = 5,
    net_debt: float = 0.0
) -> Dict[str, Any]:
    """Calculate the constant annual FCF growth rate implied by the current market price.
    Uses bisection method to solve for implied CAGR.
    """
    if discount_rate <= terminal_growth_rate:
        raise ValueError("Discount rate must be strictly greater than terminal growth rate.")
    if current_price <= 0 or shares_outstanding <= 0:
        raise ValueError("Current price and shares outstanding must be positive.")
        
    target_equity_value = (current_price * shares_outstanding)
    
    def price_diff(g: float) -> float:
        # DCF valuation with constant growth rate g for projection_years
        growth_rates = [g] * projection_years
        res = dcf(
            base_fcf=base_fcf,
            growth_rates=growth_rates,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate,
            shares_outstanding=shares_outstanding,
            net_debt=net_debt
        )
        return res["result"]["equity_value"] - target_equity_value
        
    # Initial search range for growth rate
    low = -0.50
    high = 2.00
    
    diff_low = price_diff(low)
    diff_high = price_diff(high)
    
    # Adaptive dynamic bound expansion (elasticity)
    # If target price requires higher growth, expand high bound up to 20.0 (+2000%)
    expand_iter = 0
    while diff_high < 0 and high < 20.0 and expand_iter < 10:
        high *= 2.0
        diff_high = price_diff(high)
        expand_iter += 1

    # If target price requires lower/negative growth, expand low bound down to -0.99 (-99%)
    expand_iter = 0
    while diff_low > 0 and low > -0.99 and expand_iter < 10:
        low = max(-0.99, low - 0.20)
        diff_low = price_diff(low)
        expand_iter += 1

    if diff_low > 0:
        implied_g = low
    elif diff_high < 0:
        implied_g = high
    else:
        # Bisection root finding
        for _ in range(120):
            mid = (low + high) / 2.0
            diff_mid = price_diff(mid)
            if abs(diff_mid) < 1e-4 or (high - low) < 1e-6:
                break
            if (diff_low * diff_mid) <= 0:
                high = mid
                diff_high = diff_mid
            else:
                low = mid
                diff_low = diff_mid
        implied_g = mid
        
    implied_g_pct = implied_g * 100.0
    return {
        "result": {
            "implied_growth_rate_pct": implied_g_pct,
            "current_price": current_price,
            "target_equity_value": target_equity_value,
            "projection_years": projection_years,
            "discount_rate": discount_rate,
            "terminal_growth_rate": terminal_growth_rate
        },
        "formula": "Solves for constant CAGR g such that DCF(g, base_fcf, WACC, g_term) == Market Cap + Net Debt",
        "inputs": {
            "current_price": current_price,
            "base_fcf": base_fcf,
            "shares_outstanding": shares_outstanding,
            "discount_rate": discount_rate,
            "terminal_growth_rate": terminal_growth_rate,
            "projection_years": projection_years,
            "net_debt": net_debt
        },
        "formatted": f"Implied {projection_years}-Year FCF CAGR: {implied_g_pct:.2f}% (at ${current_price:.2f}/share, WACC {discount_rate*100:.1f}%, Terminal g {terminal_growth_rate*100:.1f}%)"
    }
