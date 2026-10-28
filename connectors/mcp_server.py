"""
connectors/mcp_server.py - Model Context Protocol (MCP) Server
Standard JSON-RPC 2.0 / MCP Server over stdio connecting the Meridian Financial
Research Workstation, Quantitative Desks, Probability Simulator, and $1,000,000
Paper Trading Engine to external AI clients (Claude Desktop, Claude Code, Cursor, Windsurf, Roo Code).
"""

import sys
import os
import json
import traceback
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.ticker_search import lookup_primary_ticker, search_company_tickers
from tools.multi_asset_data import MultiAssetDataEngine
from tools.calc.derivatives_math import BlackScholesEngine
from tools.calc.probability_simulator import (
    EconometricProbabilitySimulator,
    cornish_fisher_quantile,
    hitting_time_touch_probability
)
from tools.paper_trading import get_paper_trading_engine, INITIAL_PORTFOLIO_CASH
from agents.meridian_orchestrator import MeridianMultiAssetOrchestrator
import yfinance as yf


# =============================================================================
# TOOL DEFINITIONS & SCHEMAS (Model Context Protocol Standard)
# =============================================================================

MCP_TOOLS = [
    {
        "name": "resolve_ticker",
        "description": "Intelligently resolves informal company names (e.g. 'micron', 'apple', 'nvidia', 'tesla') or ticker symbols (e.g. 'MU', 'AAPL', 'NVDA') to official market symbols, live quotes, ATM options strikes, and real-time implied volatility.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Company name or ticker symbol to resolve (e.g. 'apple', 'micron', 'MU', 'NVDA', 'BTC-USD')"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_live_quote",
        "description": "Fetches real-time market quote (last price, day change, day change %, volume, currency, timestamp) for any stock, ETF, crypto (e.g. 'BTC-USD'), or commodity/futures (e.g. 'CL=F', 'GC=F').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol (e.g. 'AAPL', 'MU', 'BTC-USD', 'ES=F', 'GC=F')"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_options_chain",
        "description": "Fetches live options expiration chains, strikes, bid/ask spreads, open interest, volume, put-call ratio (PCR), and implied volatility for any equity or ETF.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Underlying equity or ETF ticker (e.g. 'AAPL', 'NVDA', 'SPY')"
                },
                "expiration": {
                    "type": "string",
                    "description": "Optional ISO expiration date (YYYY-MM-DD). If omitted, selects nearest active monthly expiry."
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "calculate_options_greeks",
        "description": "Calculates institutional Black-Scholes fair value and first/second-order Greeks (Delta, Gamma, Theta, Vega, Rho, Vanna, Volga) for a specific call or put option contract.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spot": {
                    "type": "number",
                    "description": "Current price of the underlying asset in USD"
                },
                "strike": {
                    "type": "number",
                    "description": "Option strike price in USD"
                },
                "dte": {
                    "type": "integer",
                    "description": "Calendar days to expiration"
                },
                "iv": {
                    "type": "number",
                    "description": "Implied volatility as decimal (e.g. 0.35 for 35%)"
                },
                "r": {
                    "type": "number",
                    "description": "Annualized risk-free interest rate (default: 0.045 for 4.5%)",
                    "default": 0.045
                },
                "option_type": {
                    "type": "string",
                    "enum": ["call", "put"],
                    "description": "Option type: 'call' or 'put'",
                    "default": "call"
                }
            },
            "required": ["spot", "strike", "dte", "iv"]
        }
    },
    {
        "name": "analyze_options_strategy",
        "description": "Evaluates multi-leg options strategies (Iron Condor, Straddle, Strangle, Bull Call Spread, Bear Put Spread, Collar, Covered Call). Returns net debit/credit, max profit, max loss, breakeven points, risk/reward ratio, and strategic payoff curve.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Underlying asset ticker symbol"
                },
                "spot": {
                    "type": "number",
                    "description": "Current spot price in USD"
                },
                "legs": {
                    "type": "array",
                    "description": "List of strategy legs",
                    "items": {
                        "type": "object",
                        "properties": {
                            "strike": {"type": "number"},
                            "option_type": {"type": "string", "enum": ["call", "put", "stock"]},
                            "side": {"type": "string", "enum": ["buy", "sell"]},
                            "premium": {"type": "number"},
                            "quantity": {"type": "number", "default": 1.0},
                            "dte": {"type": "integer", "default": 30}
                        },
                        "required": ["strike", "option_type", "side", "premium"]
                    }
                }
            },
            "required": ["symbol", "spot", "legs"]
        }
    },
    {
        "name": "simulate_econometric_probability",
        "description": "Runs quantitative econometric simulations conforming to Black-Scholes and Bloomberg OVME standards: Log-normal PDF/CDF probability cones (+/- 1, 2, 3 sigma), probability of reaching or touching price targets (hitting time / barrier touch), options probability of profit (POP), and Cornish-Fisher skewness/kurtosis-adjusted VaR/CVaR.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["pdf_cdf", "single_stock", "options_strategy", "cornish_fisher"],
                    "description": "Simulation mode to run"
                },
                "spot": {
                    "type": "number",
                    "description": "Current underlying spot price"
                },
                "dte": {
                    "type": "integer",
                    "description": "Days to expiration horizon",
                    "default": 30
                },
                "volatility": {
                    "type": "number",
                    "description": "Annualized volatility as decimal (e.g. 0.25)",
                    "default": 0.25
                },
                "target_price": {
                    "type": "number",
                    "description": "Target price for single-stock probability simulation"
                },
                "drift": {
                    "type": "number",
                    "description": "Expected annualized drift / return",
                    "default": 0.045
                },
                "lower_barrier": {
                    "type": "number",
                    "description": "Downside touch barrier price"
                },
                "upper_barrier": {
                    "type": "number",
                    "description": "Upside touch barrier price"
                },
                "legs": {
                    "type": "array",
                    "description": "Options legs for strategy simulation"
                }
            },
            "required": ["mode", "spot"]
        }
    },
    {
        "name": "execute_paper_trade",
        "description": "Executes an institutional paper order mirroring live market conditions against the $1,000,000.00 simulation portfolio. Supports Equities, Options (x100 multiplier), Futures (CME initial margin), and Crypto Perpetuals. Signs execution receipt with cryptographic HMAC-SHA256 ledger.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Asset ticker symbol"
                },
                "asset_class": {
                    "type": "string",
                    "enum": ["Equities", "Options", "Futures", "Crypto", "Fixed Income"],
                    "description": "Asset class of the trade"
                },
                "side": {
                    "type": "string",
                    "enum": ["BUY", "SELL"],
                    "description": "Order side"
                },
                "quantity": {
                    "type": "number",
                    "description": "Quantity or number of contracts/shares"
                },
                "price": {
                    "type": "number",
                    "description": "Execution price per unit in USD"
                },
                "strategy_type": {
                    "type": "string",
                    "description": "Strategy label (e.g. 'Standard', 'Covered Call', 'Momentum Breakout')",
                    "default": "Standard"
                },
                "multiplier": {
                    "type": "number",
                    "description": "Contract multiplier (e.g. 100 for equity options, 50 for ES futures)",
                    "default": 1.0
                },
                "margin_per_unit": {
                    "type": "number",
                    "description": "Margin requirement per contract (for Futures)",
                    "default": 0.0
                },
                "notes": {
                    "type": "string",
                    "description": "Optional trade thesis or rationale",
                    "default": ""
                }
            },
            "required": ["symbol", "asset_class", "side", "quantity", "price"]
        }
    },
    {
        "name": "get_paper_portfolio",
        "description": "Retrieves real-time paper trading portfolio status: total equity, available cash balance, active open positions, cost bases, current market values, total unrealized P&L, realized P&L, and portfolio return %.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "close_paper_position",
        "description": "Closes an active position in the $1,000,000 paper trading portfolio at the specified or live market price. Realizes P&L, credits cash balance, and generates cryptographic provenance receipt.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "position_id": {
                    "type": "string",
                    "description": "Position ID to close (e.g. 'POS_0001')"
                },
                "exit_price": {
                    "type": "number",
                    "description": "Optional exit price. If omitted, fetches live market quote automatically."
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for closing position (default: 'Market Close')",
                    "default": "Market Close"
                }
            },
            "required": ["position_id"]
        }
    },
    {
        "name": "run_multi_asset_committee",
        "description": "Convenes the institutional 5-Desk Multi-Asset Investment Committee (Options Greek Strategist, Futures & Commodity Desk, Fixed Income Macro Agent, Crypto Derivatives Agent, and Cross-Asset Risk Officer) to audit a multi-asset portfolio, conduct crisis stress tests, evaluate leverage/margin, and issue CRO signoff.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "portfolio_name": {
                    "type": "string",
                    "description": "Name or identifier of the portfolio"
                },
                "total_capital": {
                    "type": "number",
                    "description": "Total investment capital in USD (e.g. 1000000.0)"
                },
                "allocations": {
                    "type": "object",
                    "description": "Dollar allocation dictionary across asset classes (e.g. {'Equities': 400000.0, 'Options': 100000.0, 'Futures': 200000.0, 'Crypto': 100000.0, 'Fixed Income': 200000.0})"
                }
            },
            "required": ["portfolio_name", "total_capital", "allocations"]
        }
    }
]


# =============================================================================
# TOOL EXECUTION DISPATCHER
# =============================================================================

def handle_resolve_ticker(query: str) -> Dict[str, Any]:
    clean_q = (query or "").strip()
    sym = lookup_primary_ticker(clean_q) or clean_q.upper()
    sym = sym.strip().upper()

    name = sym
    exchange = "US"
    asset_type = "EQUITY"
    try:
        matches = search_company_tickers(clean_q, max_results=3)
        for m in matches:
            if m.get("symbol", "").upper() == sym:
                name = m.get("name", sym)
                exchange = m.get("exchange", "US")
                asset_type = m.get("type", "EQUITY")
                break
        if name == sym and matches:
            name = matches[0].get("name", sym)
            exchange = matches[0].get("exchange", "US")
            asset_type = matches[0].get("type", "EQUITY")
    except Exception:
        pass

    price = 0.0
    change_pct = 0.0
    currency = "USD"
    try:
        t = yf.Ticker(sym)
        fi = getattr(t, "fast_info", None)
        p_val = getattr(fi, "last_price", None) or getattr(fi, "previous_close", None)
        if p_val and float(p_val) > 0:
            price = float(p_val)
            prev = getattr(fi, "previous_close", price)
            if prev and prev > 0:
                change_pct = ((price - prev) / prev) * 100.0
            currency = getattr(fi, "currency", "USD") or "USD"
    except Exception:
        price = 100.0

    atm_strike = price
    atm_iv_pct = 35.0
    dte = 30
    expirations: List[str] = []
    pcr_oi = 1.0
    selected_expiry = ""

    try:
        m_engine = MultiAssetDataEngine()
        opt = m_engine.get_options_chain(sym)
        if opt:
            atm_strike = float(opt.get("atm_strike", price))
            expirations = opt.get("available_expirations", [])
            selected_expiry = opt.get("selected_expiration", "")
            pcr_oi = float(opt.get("put_call_ratio_oi", 1.0))
            if selected_expiry:
                import datetime
                try:
                    exp_date = datetime.date.fromisoformat(selected_expiry)
                    dte = max(1, (exp_date - datetime.date.today()).days)
                except Exception:
                    dte = 30
            atm_calls = [c for c in opt.get("calls", []) if abs(c["strike"] - atm_strike) < 0.01]
            if atm_calls and atm_calls[0].get("iv_pct", 0.0) > 0:
                atm_iv_pct = float(atm_calls[0]["iv_pct"])
            elif opt.get("calls"):
                closest = min(opt["calls"], key=lambda c: abs(c["strike"] - atm_strike))
                if closest.get("iv_pct", 0.0) > 0:
                    atm_iv_pct = float(closest["iv_pct"])
    except Exception:
        pass

    return {
        "query": clean_q,
        "symbol": sym,
        "name": name,
        "exchange": exchange,
        "type": asset_type,
        "price": round(price, 2) if price > 0 else 100.0,
        "change_pct": round(change_pct, 2),
        "currency": currency,
        "atm_strike": round(atm_strike, 2) if atm_strike > 0 else round(price, 2),
        "atm_iv_pct": round(atm_iv_pct, 1) if atm_iv_pct > 0 else 35.0,
        "dte": int(dte),
        "expirations": expirations,
        "selected_expiry": selected_expiry,
        "pcr_oi": round(pcr_oi, 2),
        "resolved": True
    }


def handle_get_live_quote(symbol: str) -> Dict[str, Any]:
    sym = (symbol or "").strip().upper()
    try:
        t = yf.Ticker(sym)
        fi = getattr(t, "fast_info", None)
        price = float(getattr(fi, "last_price", None) or getattr(fi, "previous_close", None) or 100.0)
        prev = float(getattr(fi, "previous_close", None) or price)
        change = price - prev
        change_pct = ((price - prev) / prev * 100.0) if prev > 0 else 0.0
        volume = float(getattr(fi, "last_volume", None) or 0.0)
        currency = getattr(fi, "currency", "USD") or "USD"
        return {
            "symbol": sym,
            "last_price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": volume,
            "currency": currency,
            "status": "LIVE"
        }
    except Exception as e:
        return {
            "symbol": sym,
            "last_price": 100.0,
            "change": 0.0,
            "change_pct": 0.0,
            "volume": 0.0,
            "currency": "USD",
            "status": f"Fallback quote ({str(e)})"
        }


def handle_get_options_chain(symbol: str, expiration: Optional[str] = None) -> Dict[str, Any]:
    m_engine = MultiAssetDataEngine()
    chain = m_engine.get_options_chain(symbol=symbol, expiration=expiration)
    # Simplify payload for LLM consumption
    return {
        "underlying_symbol": chain.get("underlying_symbol"),
        "underlying_price": chain.get("underlying_price"),
        "available_expirations": chain.get("available_expirations", []),
        "selected_expiration": chain.get("selected_expiration"),
        "atm_strike": chain.get("atm_strike"),
        "put_call_ratio_oi": chain.get("put_call_ratio_oi"),
        "total_call_oi": chain.get("total_call_oi"),
        "total_put_oi": chain.get("total_put_oi"),
        "calls_count": len(chain.get("calls", [])),
        "puts_count": len(chain.get("puts", [])),
        "sample_atm_calls": chain.get("calls", [])[:5],
        "sample_atm_puts": chain.get("puts", [])[:5]
    }


def handle_calculate_options_greeks(
    spot: float,
    strike: float,
    dte: int,
    iv: float,
    r: float = 0.045,
    option_type: str = "call"
) -> Dict[str, Any]:
    t_years = max(1, dte) / 365.0
    opt_type_clean = option_type.lower().strip()

    greeks = BlackScholesEngine.price_and_greeks(
        spot=spot,
        strike=strike,
        time_to_expiry=t_years,
        risk_free_rate=r,
        volatility=iv,
        dividend_yield=0.0,
        option_type=opt_type_clean
    )

    return {
        "spot": spot,
        "strike": strike,
        "dte": dte,
        "iv": iv,
        "risk_free_rate": r,
        "option_type": opt_type_clean,
        "fair_value": greeks["price"],
        "delta": greeks["delta"],
        "gamma": greeks["gamma"],
        "theta_per_day": greeks["theta_daily"],
        "vega_per_1pct": greeks["vega"],
        "rho": greeks["rho"],
        "vanna": greeks["vanna"],
        "volga": greeks["volga"]
    }


def handle_analyze_options_strategy(
    symbol: str,
    spot: float,
    legs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    bs = BlackScholesEngine()
    result = bs.calculate_multi_leg_strategy(
        strategy_name=f"Custom Strategy ({symbol})",
        spot=spot,
        legs=legs,
        r=0.045
    )
    return result


def handle_simulate_econometric_probability(
    mode: str,
    spot: float,
    dte: int = 30,
    volatility: float = 0.25,
    target_price: Optional[float] = None,
    drift: float = 0.045,
    lower_barrier: Optional[float] = None,
    upper_barrier: Optional[float] = None,
    legs: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    sim = EconometricProbabilitySimulator()
    t_years = max(1, dte) / 365.0

    if mode == "pdf_cdf":
        cone = sim.calculate_lognormal_distribution(
            spot=spot,
            volatility=volatility,
            time_years=t_years,
            drift=drift
        )
        return {
            "mode": "pdf_cdf",
            "spot": spot,
            "dte": dte,
            "volatility": volatility,
            "expected_ranges": cone.get("sigma_cones"),
            "drift_parameters": cone.get("parameters")
        }

    elif mode == "single_stock":
        tgt = target_price if target_price and target_price > 0 else round(spot * 1.05, 2)
        stop = lower_barrier if lower_barrier and lower_barrier > 0 else round(spot * 0.95, 2)
        res = sim.simulate_equity_probability(
            spot=spot,
            target_price=tgt,
            stop_loss_price=stop,
            horizon_days=dte,
            volatility=volatility,
            drift=drift
        )
        return res

    elif mode == "options_strategy":
        sample_legs = legs or [
            {"strike": round(spot, 2), "option_type": "call", "side": "buy", "premium": round(spot * 0.03, 2), "dte": dte, "volatility": volatility}
        ]
        res = sim.simulate_options_strategy_probability(
            spot=spot,
            legs=sample_legs,
            drift=drift
        )
        return res

    elif mode == "cornish_fisher":
        z_norm_95 = 1.644853
        z_norm_99 = 2.326348
        z_95 = cornish_fisher_quantile(z_norm_95, skewness=-0.5, excess_kurtosis=1.5)
        z_99 = cornish_fisher_quantile(z_norm_99, skewness=-0.5, excess_kurtosis=1.5)
        var_95_pct = abs(z_95) * volatility * (t_years ** 0.5) * 100.0
        var_99_pct = abs(z_99) * volatility * (t_years ** 0.5) * 100.0
        return {
            "mode": "cornish_fisher",
            "spot": spot,
            "horizon_days": dte,
            "volatility_annualized": volatility,
            "assumed_skewness": -0.5,
            "assumed_excess_kurtosis": 1.5,
            "cornish_fisher_z_95": round(z_95, 4),
            "cornish_fisher_z_99": round(z_99, 4),
            "parametric_var_95_pct": round(var_95_pct, 2),
            "parametric_var_99_pct": round(var_99_pct, 2),
            "dollar_var_95": round(spot * (var_95_pct / 100.0), 2),
            "dollar_var_99": round(spot * (var_99_pct / 100.0), 2)
        }

    else:
        raise ValueError(f"Unknown simulation mode '{mode}'. Choose from: pdf_cdf, single_stock, options_strategy, cornish_fisher")


def handle_execute_paper_trade(
    symbol: str,
    asset_class: str,
    side: str,
    quantity: float,
    price: float,
    strategy_type: str = "Standard",
    multiplier: float = 1.0,
    margin_per_unit: float = 0.0,
    notes: str = "",
    thesis: Optional[str] = None,
    invalidation_condition: Optional[str] = None,
    review_date: Optional[Any] = None
) -> Dict[str, Any]:
    engine = get_paper_trading_engine()
    clean_thesis = thesis or (notes if len(notes) >= 5 else f"Systematic execution thesis for {symbol}")
    clean_inval = invalidation_condition or f"Market adverse regime shift or stop loss trigger for {symbol}"
    clean_rev = review_date or (datetime.date.today() + datetime.timedelta(days=30)).isoformat()

    success, msg, pos = engine.execute_trade(
        symbol=symbol,
        asset_class=asset_class,
        side=side,
        quantity=quantity,
        price=price,
        strategy_type=strategy_type,
        multiplier=multiplier,
        margin_per_unit=margin_per_unit,
        notes=notes,
        thesis=clean_thesis,
        invalidation_condition=clean_inval,
        review_date=clean_rev
    )
    portfolio = engine.load_portfolio()
    return {
        "success": success,
        "message": msg,
        "trade": pos,
        "remaining_cash": portfolio.get("cash_balance"),
        "total_equity": portfolio.get("total_equity")
    }


def handle_get_paper_portfolio() -> Dict[str, Any]:
    engine = get_paper_trading_engine()
    engine.mark_to_market()
    data = engine.load_portfolio()
    return {
        "initial_cash": data.get("initial_cash", INITIAL_PORTFOLIO_CASH),
        "cash_balance": data.get("cash_balance"),
        "total_equity": data.get("total_equity"),
        "total_unrealized_pnl": data.get("total_unrealized_pnl"),
        "total_realized_pnl": data.get("total_realized_pnl"),
        "portfolio_return_pct": data.get("portfolio_return_pct", 0.0),
        "open_positions_count": len(data.get("positions", [])),
        "positions": data.get("positions", []),
        "closed_trades_count": len(data.get("closed_trades", []))
    }


def handle_close_paper_position(
    position_id: str,
    exit_price: Optional[float] = None,
    reason: str = "Market Close"
) -> Dict[str, Any]:
    engine = get_paper_trading_engine()
    success, msg, closed = engine.close_position(
        position_id=position_id,
        exit_price=exit_price,
        reason=reason
    )
    portfolio = engine.load_portfolio()
    return {
        "success": success,
        "message": msg,
        "closed_trade": closed,
        "new_cash_balance": portfolio.get("cash_balance"),
        "total_equity": portfolio.get("total_equity"),
        "total_realized_pnl": portfolio.get("total_realized_pnl")
    }


def handle_run_multi_asset_committee(
    portfolio_name: str,
    total_capital: float,
    allocations: Dict[str, float]
) -> Dict[str, Any]:
    orch = MeridianMultiAssetOrchestrator()
    report = orch.run_multi_asset_committee(
        portfolio_name=portfolio_name,
        total_capital_usd=total_capital,
        allocations_usd=allocations
    )
    return report


def dispatch_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tool by name with arguments."""
    if tool_name == "resolve_ticker":
        return handle_resolve_ticker(arguments.get("query", ""))
    elif tool_name == "get_live_quote":
        return handle_get_live_quote(arguments.get("symbol", ""))
    elif tool_name == "get_options_chain":
        return handle_get_options_chain(
            symbol=arguments.get("symbol", ""),
            expiration=arguments.get("expiration")
        )
    elif tool_name == "calculate_options_greeks":
        return handle_calculate_options_greeks(
            spot=float(arguments["spot"]),
            strike=float(arguments["strike"]),
            dte=int(arguments["dte"]),
            iv=float(arguments["iv"]),
            r=float(arguments.get("r", 0.045)),
            option_type=arguments.get("option_type", "call")
        )
    elif tool_name == "analyze_options_strategy":
        return handle_analyze_options_strategy(
            symbol=arguments["symbol"],
            spot=float(arguments["spot"]),
            legs=arguments["legs"]
        )
    elif tool_name == "simulate_econometric_probability":
        return handle_simulate_econometric_probability(
            mode=arguments["mode"],
            spot=float(arguments["spot"]),
            dte=int(arguments.get("dte", 30)),
            volatility=float(arguments.get("volatility", 0.25)),
            target_price=float(arguments["target_price"]) if "target_price" in arguments and arguments["target_price"] is not None else None,
            drift=float(arguments.get("drift", 0.045)),
            lower_barrier=float(arguments["lower_barrier"]) if "lower_barrier" in arguments and arguments["lower_barrier"] is not None else None,
            upper_barrier=float(arguments["upper_barrier"]) if "upper_barrier" in arguments and arguments["upper_barrier"] is not None else None,
            legs=arguments.get("legs")
        )
    elif tool_name == "execute_paper_trade":
        return handle_execute_paper_trade(
            symbol=arguments["symbol"],
            asset_class=arguments["asset_class"],
            side=arguments["side"],
            quantity=float(arguments["quantity"]),
            price=float(arguments["price"]),
            strategy_type=arguments.get("strategy_type", "Standard"),
            multiplier=float(arguments.get("multiplier", 1.0)),
            margin_per_unit=float(arguments.get("margin_per_unit", 0.0)),
            notes=arguments.get("notes", ""),
            thesis=arguments.get("thesis"),
            invalidation_condition=arguments.get("invalidation_condition"),
            review_date=arguments.get("review_date")
        )
    elif tool_name == "get_paper_portfolio":
        return handle_get_paper_portfolio()
    elif tool_name == "close_paper_position":
        exit_p = float(arguments["exit_price"]) if "exit_price" in arguments and arguments["exit_price"] is not None else None
        return handle_close_paper_position(
            position_id=arguments["position_id"],
            exit_price=exit_p,
            reason=arguments.get("reason", "Market Close")
        )
    elif tool_name == "run_multi_asset_committee":
        return handle_run_multi_asset_committee(
            portfolio_name=arguments["portfolio_name"],
            total_capital=float(arguments["total_capital"]),
            allocations=arguments["allocations"]
        )
    else:
        raise ValueError(f"Unknown tool '{tool_name}'")


# =============================================================================
# JSON-RPC 2.0 / MCP PROTOCOL ENGINE OVER STDIO
# =============================================================================

def send_json_response(payload: Dict[str, Any]) -> None:
    """Send single-line JSON message on stdout followed by newline."""
    json_str = json.dumps(payload)
    sys.stdout.write(json_str + "\n")
    sys.stdout.flush()


def log_debug(msg: str) -> None:
    """Log strictly to stderr so stdout JSON-RPC framing is never contaminated."""
    sys.stderr.write(f"[MCP Server] {msg}\n")
    sys.stderr.flush()


def process_message(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process incoming JSON-RPC 2.0 MCP message."""
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params", {})

    log_debug(f"Handling method: {method} (id: {req_id})")

    # 1. MCP Handshake / Initialization
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "meridian-finance-workstation",
                    "version": "1.0.0"
                }
            }
        }

    # 2. Initialized Notification (no response needed per JSON-RPC)
    elif method == "notifications/initialized":
        log_debug("Client initialized.")
        return None

    # 3. Ping
    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }

    # 4. List Tools
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }

    # 5. Call Tool
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            result_data = dispatch_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result_data, indent=2)
                        }
                    ],
                    "isError": False
                }
            }
        except Exception as e:
            err_msg = f"Error executing tool '{tool_name}': {str(e)}\n{traceback.format_exc()}"
            log_debug(err_msg)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "error": str(e),
                                "tool": tool_name,
                                "traceback": traceback.format_exc()
                            }, indent=2)
                        }
                    ],
                    "isError": True
                }
            }

    # 6. Resources List (Standard MCP fallback)
    elif method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"resources": []}
        }

    # 7. Prompts List (Standard MCP fallback)
    elif method == "prompts/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"prompts": []}
        }

    # Unknown method
    else:
        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found"
                }
            }
        return None


def run_mcp_server() -> None:
    """Run JSON-RPC MCP server reading line-by-line from stdin."""
    log_debug("Meridian Finance MCP Server started. Listening on stdin...")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            line_clean = line.strip()
            if not line_clean:
                continue

            # Support Content-Length header framing if client sends HTTP-like headers
            if line_clean.lower().startswith("content-length:"):
                try:
                    content_length = int(line_clean.split(":")[1].strip())
                    # Consume following blank lines
                    while True:
                        hdr = sys.stdin.readline().strip()
                        if not hdr:
                            break
                    body = sys.stdin.read(content_length)
                    request = json.loads(body)
                except Exception as e:
                    log_debug(f"Error parsing content-length body: {e}")
                    continue
            else:
                # Standard line-delimited JSON
                try:
                    request = json.loads(line_clean)
                except json.JSONDecodeError as e:
                    log_debug(f"JSON decode error: {e} for line: {line_clean}")
                    continue

            response = process_message(request)
            if response is not None:
                send_json_response(response)

        except KeyboardInterrupt:
            log_debug("Server terminated by user.")
            break
        except Exception as e:
            log_debug(f"Unexpected loop exception: {e}\n{traceback.format_exc()}")


if __name__ == "__main__":
    run_mcp_server()
