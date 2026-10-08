"""
Financial Calculation Toolkit Module
Tested, deterministic financial calculation functions for Antigravity research agents.
"""

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
from tools.calc.dcf import (
    dcf,
    reverse_dcf,
    dcf_sensitivity_matrix
)
from tools.calc.fx import (
    convert_currency
)
from tools.calc.portfolio_opt import (
    PortfolioQPOptimizer
)
from tools.calc.supply_chain_opt import (
    SupplyChainLogisticsOptimizer
)
from tools.calc.gpu_autotune_sim import (
    FinancialKernelAutotuner
)

__all__ = [
    "yoy_growth",
    "cagr",
    "margin",
    "roic",
    "roe",
    "free_cash_flow",
    "fcf_yield",
    "net_debt_to_ebitda",
    "interest_coverage",
    "cash_conversion",
    "enterprise_value",
    "ev_multiples",
    "dcf",
    "reverse_dcf",
    "dcf_sensitivity_matrix",
    "convert_currency",
    "PortfolioQPOptimizer",
    "SupplyChainLogisticsOptimizer",
    "FinancialKernelAutotuner"
]

