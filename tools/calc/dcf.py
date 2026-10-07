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
    net_debt: float = 0.0,
    currency: str = "USD",
    currency_symbol: str = "$"
) -> Dict[str, Any]:
    """Calculate Discounted Cash Flow (DCF) Enterprise & Equity Value per share.
    
    Args:
        base_fcf: Most recent fiscal year Free Cash Flow.
        growth_rates: List of expected annual FCF growth rates.
        discount_rate: WACC or hurdle rate.
        terminal_growth_rate: Perpetual terminal growth rate (< discount_rate).
        shares_outstanding: Diluted share count (> 0).
        net_debt: Total Debt - Liquid Cash & Equivalents.
        currency: ISO-4217 Currency Code (default: 'USD').
        currency_symbol: Currency symbol for formatting (default: '$').
    """
    if not growth_rates or len(growth_rates) == 0:
        raise ValueError("Growth rates projection list cannot be empty.")
    if len(growth_rates) > 30:
        raise ValueError("Projection horizon exceeds practical modeling limits (max 30 years).")

    # Strict numerical finiteness validation
    for val_name, val in [
        ("base_fcf", base_fcf),
        ("discount_rate", discount_rate),
        ("terminal_growth_rate", terminal_growth_rate),
        ("shares_outstanding", shares_outstanding),
        ("net_debt", net_debt),
    ]:
        if not isinstance(val, (int, float)) or not math.isfinite(val):
            raise ValueError(f"Input '{val_name}' must be a finite numerical value, got {val}.")

    for idx, g in enumerate(growth_rates):
        if not isinstance(g, (int, float)) or not math.isfinite(g):
            raise ValueError(f"Growth rate at period {idx + 1} must be finite, got {g}.")

    if discount_rate <= terminal_growth_rate:
        raise ValueError("Discount rate must be strictly greater than terminal growth rate.")
    if shares_outstanding <= 0:
        raise ValueError("Shares outstanding must be positive.")
    
    warnings = []
    if base_fcf <= 0:
        warnings.append("Base FCF is negative or zero; Gordon growth terminal value assumes eventual cash flow turnaround.")

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
            "projected_fcf": projected_fcf,
            "currency": currency,
            "currency_symbol": currency_symbol,
            "warnings": warnings
        },
        "formula": "Equity Value = Sum(PV of FCF) + PV(Terminal Value) - Net Debt; Fair Value = Equity Value / Shares",
        "inputs": {
            "base_fcf": base_fcf,
            "growth_rates": growth_rates,
            "discount_rate": discount_rate,
            "terminal_growth_rate": terminal_growth_rate,
            "shares_outstanding": shares_outstanding,
            "net_debt": net_debt,
            "currency": currency
        },
        "formatted": f"Fair Value: {currency_symbol}{fair_value_per_share:.2f}/share ({currency}) (Equity Val: {currency_symbol}{equity_value:,.2f}, EV: {currency_symbol}{enterprise_value:,.2f})"
    }

def reverse_dcf(
    current_price: float,
    base_fcf: float,
    shares_outstanding: float,
    discount_rate: float,
    terminal_growth_rate: float,
    projection_years: int = 5,
    net_debt: float = 0.0,
    currency: str = "USD",
    currency_symbol: str = "$"
) -> Dict[str, Any]:
    """Calculate the constant annual FCF growth rate implied by the current market price.
    Uses bisection method to solve for implied CAGR and returns explicit solver convergence status.
    """
    for val_name, val in [
        ("current_price", current_price),
        ("base_fcf", base_fcf),
        ("shares_outstanding", shares_outstanding),
        ("discount_rate", discount_rate),
        ("terminal_growth_rate", terminal_growth_rate),
        ("net_debt", net_debt),
    ]:
        if not isinstance(val, (int, float)) or not math.isfinite(val):
            raise ValueError(f"Input '{val_name}' must be a finite numerical value, got {val}.")

    if discount_rate <= terminal_growth_rate:
        raise ValueError("Discount rate must be strictly greater than terminal growth rate.")
    if current_price <= 0 or shares_outstanding <= 0:
        raise ValueError("Current price and shares outstanding must be positive.")
    if projection_years < 1 or projection_years > 30:
        raise ValueError("Projection horizon must be between 1 and 30 years.")
        
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
            net_debt=net_debt,
            currency=currency,
            currency_symbol=currency_symbol
        )
        return res["result"]["equity_value"] - target_equity_value
        
    # Initial search range for growth rate
    low = -0.50
    high = 2.00
    
    diff_low = price_diff(low)
    diff_high = price_diff(high)
    
    # Adaptive dynamic bound expansion (elasticity)
    expand_iter = 0
    while diff_high < 0 and high < 20.0 and expand_iter < 10:
        high *= 2.0
        diff_high = price_diff(high)
        expand_iter += 1

    expand_iter = 0
    while diff_low > 0 and low > -0.99 and expand_iter < 10:
        low = max(-0.99, low - 0.20)
        diff_low = price_diff(low)
        expand_iter += 1

    iterations_performed = 0
    if diff_low > 0:
        implied_g = low
        solver_status = "BOUND_SATURATED_MIN"
        residual = diff_low
    elif diff_high < 0:
        implied_g = high
        solver_status = "BOUND_SATURATED_MAX"
        residual = diff_high
    else:
        # Bisection root finding
        solver_status = "CONVERGED"
        for i in range(120):
            iterations_performed = i + 1
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
        residual = diff_mid
        
    implied_g_pct = implied_g * 100.0
    return {
        "result": {
            "implied_growth_rate_pct": implied_g_pct,
            "solver_status": solver_status,
            "residual": residual,
            "iterations": iterations_performed,
            "search_bounds": [low, high],
            "current_price": current_price,
            "target_equity_value": target_equity_value,
            "projection_years": projection_years,
            "discount_rate": discount_rate,
            "terminal_growth_rate": terminal_growth_rate,
            "currency": currency,
            "currency_symbol": currency_symbol
        },
        "formula": "Solves for constant CAGR g such that DCF(g, base_fcf, WACC, g_term) == Market Cap + Net Debt",
        "inputs": {
            "current_price": current_price,
            "base_fcf": base_fcf,
            "shares_outstanding": shares_outstanding,
            "discount_rate": discount_rate,
            "terminal_growth_rate": terminal_growth_rate,
            "projection_years": projection_years,
            "net_debt": net_debt,
            "currency": currency
        },
        "formatted": f"Implied {projection_years}-Year FCF CAGR: {implied_g_pct:.2f}% [{solver_status}] (at {currency_symbol}{current_price:.2f}/share {currency}, WACC {discount_rate*100:.1f}%, Terminal g {terminal_growth_rate*100:.1f}%)"
    }
