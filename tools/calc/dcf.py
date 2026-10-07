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
    cash_flow_type: str = "FCFF",
    mid_year: bool = False,
    currency: str = "USD",
    currency_symbol: str = "$"
) -> Dict[str, Any]:
    """Calculate Discounted Cash Flow (DCF) Enterprise & Equity Value per share.
    
    Args:
        base_fcf: Most recent fiscal year Free Cash Flow (FCFF or FCFE).
        growth_rates: List of expected annual FCF growth rates.
        discount_rate: WACC (for FCFF) or Cost of Equity (for FCFE).
        terminal_growth_rate: Perpetual terminal growth rate (< discount_rate).
        shares_outstanding: Diluted share count (> 0).
        net_debt: Total Debt - Liquid Cash & Equivalents.
        cash_flow_type: 'FCFF' (Unlevered Enterprise) or 'FCFE' (Levered Equity). Default: 'FCFF'.
        mid_year: Whether to apply mid-year discounting convention (t - 0.5). Default: False.
        currency: ISO-4217 Currency Code (default: 'USD').
        currency_symbol: Currency symbol for formatting (default: '$').
    """
    if cash_flow_type not in ("FCFF", "FCFE"):
        raise ValueError(f"cash_flow_type must be either 'FCFF' or 'FCFE', got '{cash_flow_type}'.")

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

    if not isinstance(cash_flow_type, str) or cash_flow_type not in ("FCFF", "FCFE"):
        raise ValueError(f"cash_flow_type must be 'FCFF' or 'FCFE', got {cash_flow_type}.")
    if discount_rate <= -1.0:
        raise ValueError("Discount rate must be strictly greater than -100%.")
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
        period_t = (i - 0.5) if mid_year else float(i)
        discount_factor = (1.0 + discount_rate) ** period_t
        pv = current_fcf / discount_factor
        projected_fcf.append(current_fcf)
        pv_fcf.append(pv)
        
    n_years = len(growth_rates)
    terminal_fcf = projected_fcf[-1] * (1.0 + terminal_growth_rate)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
    tv_period = (n_years - 0.5) if mid_year else float(n_years)
    pv_terminal_value = terminal_value / ((1.0 + discount_rate) ** tv_period)
    
    pv_explicit_cf = sum(pv_fcf)

    if cash_flow_type == "FCFF":
        enterprise_value = pv_explicit_cf + pv_terminal_value
        equity_value = enterprise_value - net_debt
    else:  # FCFE
        equity_value = pv_explicit_cf + pv_terminal_value
        enterprise_value = equity_value + net_debt

    fair_value_per_share = equity_value / shares_outstanding
    if not math.isfinite(fair_value_per_share) or not math.isfinite(equity_value) or not math.isfinite(enterprise_value):
        raise ValueError("DCF projection resulted in arithmetic overflow or non-finite valuation values.")
    
    formula_desc = (
        "FCFF Model: EV = PV(FCFF) + PV(TV); Equity Value = EV - Net Debt; Fair Value = Equity Value / Shares"
        if cash_flow_type == "FCFF" else
        "FCFE Model: Equity Value = PV(FCFE) + PV(TV); EV = Equity Value + Net Debt; Fair Value = Equity Value / Shares"
    )

    return {
        "result": {
            "fair_value_per_share": fair_value_per_share,
            "equity_value": equity_value,
            "enterprise_value": enterprise_value,
            "pv_explicit_fcf": pv_explicit_cf,
            "pv_terminal_value": pv_terminal_value,
            "terminal_value": terminal_value,
            "projected_fcf": projected_fcf,
            "cash_flow_type": cash_flow_type,
            "mid_year": mid_year,
            "currency": currency,
            "currency_symbol": currency_symbol,
            "warnings": warnings
        },
        "formula": formula_desc,
        "inputs": {
            "base_fcf": base_fcf,
            "growth_rates": growth_rates,
            "discount_rate": discount_rate,
            "terminal_growth_rate": terminal_growth_rate,
            "shares_outstanding": shares_outstanding,
            "net_debt": net_debt,
            "cash_flow_type": cash_flow_type,
            "mid_year": mid_year,
            "currency": currency
        },
        "formatted": f"Fair Value: {currency_symbol}{fair_value_per_share:.2f}/share ({currency}) [{cash_flow_type}{', Mid-Year' if mid_year else ''}] (Equity Val: {currency_symbol}{equity_value:,.2f}, EV: {currency_symbol}{enterprise_value:,.2f})"
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
    if not isinstance(projection_years, int) or isinstance(projection_years, bool) or projection_years < 1 or projection_years > 30:
        raise ValueError("Projection horizon must be an integer between 1 and 30 years.")
        
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
        high = min(20.0, high * 2.0)
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
        solver_status = "UNCONVERGED"
        for i in range(120):
            iterations_performed = i + 1
            mid = (low + high) / 2.0
            diff_mid = price_diff(mid)
            if abs(diff_mid) < 1e-4 or (high - low) < 1e-6:
                solver_status = "CONVERGED"
                break
            if (diff_low * diff_mid) <= 0:
                high = mid
                diff_high = diff_mid
            else:
                low = mid
                diff_low = diff_mid
        implied_g = mid
        residual = diff_mid
        if solver_status == "UNCONVERGED":
            solver_status = "MAX_ITERATIONS_REACHED"
        
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

def dcf_sensitivity_matrix(
    base_fcf: float,
    growth_rates: List[float],
    discount_rates: List[float],
    terminal_growth_rates: List[float],
    shares_outstanding: float,
    net_debt: float = 0.0,
    cash_flow_type: str = "FCFF",
    mid_year: bool = False,
    currency: str = "USD",
    currency_symbol: str = "$"
) -> Dict[str, Any]:
    """Generates a 2D valuation sensitivity grid (WACC / Discount Rate vs Perpetual Terminal Growth).
    
    Returns a matrix where each row corresponds to a discount rate and each column
    corresponds to a terminal growth rate, reporting the calculated fair value per share.
    Cells where terminal_growth_rate >= discount_rate are marked as None.
    Strictly validates all financial inputs, prevents key collisions, and surfaces non-singularity errors.
    """
    for name, val in [("base_fcf", base_fcf), ("shares_outstanding", shares_outstanding), ("net_debt", net_debt)]:
        if not isinstance(val, (int, float)) or not math.isfinite(val):
            raise ValueError(f"Input '{name}' must be a finite numerical value, got {val}.")
    if shares_outstanding <= 0:
        raise ValueError("shares_outstanding must be a strictly positive finite number.")

    if not growth_rates or not isinstance(growth_rates, list):
        raise ValueError("growth_rates projection list cannot be empty and must be a list.")
    for idx, g in enumerate(growth_rates):
        if not isinstance(g, (int, float)) or not math.isfinite(g):
            raise ValueError(f"growth_rates[{idx}] must be a finite numerical value, got {g}.")

    if not discount_rates or not isinstance(discount_rates, list):
        raise ValueError("discount_rates cannot be empty and must be a list.")
    for idx, r in enumerate(discount_rates):
        if not isinstance(r, (int, float)) or not math.isfinite(r) or r <= -1.0:
            raise ValueError(f"discount_rates[{idx}] must be a finite number > -1.0, got {r}.")

    if not terminal_growth_rates or not isinstance(terminal_growth_rates, list):
        raise ValueError("terminal_growth_rates cannot be empty and must be a list.")
    for idx, g in enumerate(terminal_growth_rates):
        if not isinstance(g, (int, float)) or not math.isfinite(g) or g <= -1.0:
            raise ValueError(f"terminal_growth_rates[{idx}] must be a finite number > -1.0, got {g}.")

    if not isinstance(cash_flow_type, str) or cash_flow_type not in ("FCFF", "FCFE"):
        raise ValueError(f"cash_flow_type must be 'FCFF' or 'FCFE', got {cash_flow_type}.")

    if len(discount_rates) != len(set(discount_rates)):
        raise ValueError("discount_rates must not contain duplicate values.")
    if len(terminal_growth_rates) != len(set(terminal_growth_rates)):
        raise ValueError("terminal_growth_rates must not contain duplicate values.")

    # Upfront baseline validation of DCF model inputs
    valid_pairs = [(r, g) for r in discount_rates for g in terminal_growth_rates if r > g]
    if valid_pairs:
        test_r, test_g = valid_pairs[0]
        dcf(
            base_fcf=base_fcf,
            growth_rates=growth_rates,
            discount_rate=test_r,
            terminal_growth_rate=test_g,
            shares_outstanding=shares_outstanding,
            net_debt=net_debt,
            cash_flow_type=cash_flow_type,
            mid_year=mid_year,
            currency=currency,
            currency_symbol=currency_symbol
        )

    # Format labels with full collision safety and exact single percent signs
    def make_rate_label(val: float, seen: set) -> str:
        for decimals in (1, 2, 3, 4, 6):
            formatted_num = f"{val * 100:.{decimals}f}".rstrip("0").rstrip(".")
            lbl = f"{formatted_num}%"
            if lbl not in seen:
                seen.add(lbl)
                return lbl
        lbl = f"{val * 100:.8f}%"
        seen.add(lbl)
        return lbl

    seen_r: set = set()
    r_map = {r: make_rate_label(r, seen_r) for r in sorted(discount_rates)}

    seen_g: set = set()
    g_map = {g: make_rate_label(g, seen_g) for g in sorted(terminal_growth_rates)}

    matrix: Dict[str, Dict[str, Optional[float]]] = {}
    
    for r in sorted(discount_rates):
        r_label = r_map[r]
        matrix[r_label] = {}
        for g in sorted(terminal_growth_rates):
            g_label = g_map[g]
            if g >= r:
                matrix[r_label][g_label] = None
            else:
                res = dcf(
                    base_fcf=base_fcf,
                    growth_rates=growth_rates,
                    discount_rate=r,
                    terminal_growth_rate=g,
                    shares_outstanding=shares_outstanding,
                    net_debt=net_debt,
                    cash_flow_type=cash_flow_type,
                    mid_year=mid_year,
                    currency=currency,
                    currency_symbol=currency_symbol
                )
                matrix[r_label][g_label] = round(res["result"]["fair_value_per_share"], 2)

    return {
        "matrix": matrix,
        "discount_rates": sorted(discount_rates),
        "terminal_growth_rates": sorted(terminal_growth_rates),
        "cash_flow_type": cash_flow_type,
        "mid_year": mid_year,
        "currency": currency,
        "currency_symbol": currency_symbol
    }
