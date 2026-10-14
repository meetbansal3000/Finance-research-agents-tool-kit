"""Antigravity financial analysis tools integrated into the research toolkit."""

import yfinance as yf
import numpy as np
from typing import Optional
from google.antigravity import ToolContext


def get_stock_quote(symbol: str) -> dict:
    """Fetches real-time price, trading range, market cap, and valuation metrics for a stock.

    Args:
        symbol: The stock ticker symbol (e.g. 'GOOGL', 'AAPL', 'MSFT', 'NVDA').
    """
    symbol = symbol.strip().upper()
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        fast_info = ticker.fast_info
        current_price = fast_info.get("last_price") or info.get("currentPrice") or info.get("regularMarketPrice")
        previous_close = fast_info.get("previous_close") or info.get("previousClose")
        
        change = round(current_price - previous_close, 2) if (current_price and previous_close) else None
        change_pct = round((change / previous_close) * 100, 2) if (change and previous_close) else None

        return {
            "symbol": symbol,
            "currency": fast_info.get("currency", info.get("currency", "USD")),
            "current_price": round(float(current_price), 2) if current_price else None,
            "change": change,
            "change_percent": f"{change_pct}%" if change_pct is not None else None,
            "previous_close": round(float(previous_close), 2) if previous_close else None,
            "day_high": round(float(fast_info.get("day_high", 0)), 2) if fast_info.get("day_high") else None,
            "day_low": round(float(fast_info.get("day_low", 0)), 2) if fast_info.get("day_low") else None,
            "fifty_two_week_high": round(float(fast_info.get("year_high", 0)), 2) if fast_info.get("year_high") else info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": round(float(fast_info.get("year_low", 0)), 2) if fast_info.get("year_low") else info.get("fiftyTwoWeekLow"),
            "market_cap": fast_info.get("market_cap") or info.get("marketCap"),
            "volume": fast_info.get("last_volume") or info.get("regularMarketVolume"),
            "pe_ratio": round(float(info.get("trailingPE", 0)), 2) if info.get("trailingPE") else None,
            "forward_pe": round(float(info.get("forwardPE", 0)), 2) if info.get("forwardPE") else None,
            "dividend_yield": f"{round(float(info.get('dividendYield', 0)) * 100, 2)}%" if info.get("dividendYield") else "N/A",
        }
    except Exception as e:
        return {"error": f"Failed to retrieve quote for {symbol}: {str(e)}"}


def get_historical_performance(symbol: str, period: str = "1mo") -> dict:
    """Analyzes historical stock performance, returns, and annualized volatility over a timeframe.

    Args:
        symbol: The stock ticker symbol (e.g. 'GOOGL', 'AMZN').
        period: Timeframe: '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'ytd', 'max'.
    """
    symbol = symbol.strip().upper()
    valid_periods = ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"]
    if period not in valid_periods:
        period = "1mo"
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            return {"error": f"No historical price data found for {symbol} ({period})."}
        start_price = float(hist["Close"].iloc[0])
        end_price = float(hist["Close"].iloc[-1])
        total_return_pct = round(((end_price - start_price) / start_price) * 100, 2)
        daily_returns = hist["Close"].pct_change().dropna()
        annualized_volatility_pct = round(float(daily_returns.std()) * np.sqrt(252) * 100, 2) if not daily_returns.empty else 0.0

        return {
            "symbol": symbol,
            "period": period,
            "trading_days": len(hist),
            "start_date": str(hist.index[0].date()),
            "end_date": str(hist.index[-1].date()),
            "start_price": round(start_price, 2),
            "end_price": round(end_price, 2),
            "total_return_percent": f"{total_return_pct}%",
            "period_high": round(float(hist["High"].max()), 2),
            "period_low": round(float(hist["Low"].min()), 2),
            "annualized_volatility": f"{annualized_volatility_pct}%",
        }
    except Exception as e:
        return {"error": f"Failed to retrieve historical performance for {symbol}: {str(e)}"}


def get_financial_metrics(symbol: str) -> dict:
    """Retrieves fundamental health metrics: margins, cash flow, debt-to-equity, and ROE.

    Args:
        symbol: The stock ticker symbol (e.g. 'MSFT', 'NVDA', 'AAPL').
    """
    symbol = symbol.strip().upper()
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        return {
            "symbol": symbol,
            "company_name": info.get("longName") or info.get("shortName"),
            "revenue_growth_yoy": f"{round(float(info.get('revenueGrowth', 0)) * 100, 2)}%" if info.get("revenueGrowth") else None,
            "gross_margins": f"{round(float(info.get('grossMargins', 0)) * 100, 2)}%" if info.get("grossMargins") else None,
            "operating_margins": f"{round(float(info.get('operatingMargins', 0)) * 100, 2)}%" if info.get("operatingMargins") else None,
            "profit_margins": f"{round(float(info.get('profitMargins', 0)) * 100, 2)}%" if info.get("profitMargins") else None,
            "debt_to_equity": round(float(info.get("debtToEquity", 0)), 2) if info.get("debtToEquity") else None,
            "current_ratio": round(float(info.get("currentRatio", 0)), 2) if info.get("currentRatio") else None,
            "return_on_equity_roe": f"{round(float(info.get('returnOnEquity', 0)) * 100, 2)}%" if info.get("returnOnEquity") else None,
            "trailing_pe": round(float(info.get("trailingPE", 0)), 2) if info.get("trailingPE") else None,
            "forward_pe": round(float(info.get("forwardPE", 0)), 2) if info.get("forwardPE") else None,
            "beta": round(float(info.get("beta", 0)), 2) if info.get("beta") else None,
        }
    except Exception as e:
        return {"error": f"Failed to retrieve metrics for {symbol}: {str(e)}"}


def manage_portfolio(
    action: str,
    symbol: str = "",
    shares: float = 0.0,
    cost_basis: float = 0.0,
    ctx: Optional[ToolContext] = None,
) -> dict:
    """Manages the user's investment portfolio state across conversation turns using ToolContext.

    Args:
        action: 'view', 'add', 'remove', or 'clear'.
        symbol: Stock ticker symbol.
        shares: Number of shares.
        cost_basis: Purchase price per share.
        ctx: Antigravity ToolContext injected automatically.
    """
    action = action.lower().strip()
    portfolio = {}
    if ctx is not None:
        portfolio = ctx.get_state("portfolio_holdings", {})

    symbol = symbol.strip().upper()

    if action == "add":
        if not symbol or shares <= 0:
            return {"error": "Valid stock symbol and positive shares required."}
        current_holding = portfolio.get(symbol, {"shares": 0.0, "total_cost": 0.0})
        total_shares = current_holding["shares"] + shares
        total_cost = current_holding["total_cost"] + (shares * (cost_basis if cost_basis > 0 else 0.0))
        avg_price = (total_cost / total_shares) if (total_shares > 0 and total_cost > 0) else cost_basis
        portfolio[symbol] = {"shares": total_shares, "cost_basis": round(avg_price, 2), "total_cost": round(total_cost, 2)}
        if ctx is not None:
            ctx.set_state("portfolio_holdings", portfolio)

    elif action == "remove":
        if not symbol:
            return {"error": "Symbol required to remove position."}
        if symbol in portfolio:
            if shares <= 0 or shares >= portfolio[symbol]["shares"]:
                del portfolio[symbol]
            else:
                portfolio[symbol]["shares"] -= shares
                portfolio[symbol]["total_cost"] = portfolio[symbol]["shares"] * portfolio[symbol]["cost_basis"]
            if ctx is not None:
                ctx.set_state("portfolio_holdings", portfolio)
        else:
            return {"error": f"Symbol {symbol} not found in portfolio."}

    elif action == "clear":
        if ctx is not None:
            ctx.set_state("portfolio_holdings", {})
        return {"status": "Portfolio cleared.", "holdings": []}

    holdings_summary = []
    total_market_val = 0.0
    total_cost = 0.0

    for sym, pos in portfolio.items():
        sh = pos["shares"]
        cb = pos["cost_basis"]
        curr_price = None
        try:
            curr_price = yf.Ticker(sym).fast_info.get("last_price")
        except Exception:
            curr_price = cb
        curr_price = curr_price or cb
        mkt_val = round(sh * curr_price, 2)
        cost_val = round(sh * cb, 2)
        total_market_val += mkt_val
        total_cost += cost_val

        holdings_summary.append({
            "symbol": sym,
            "shares": sh,
            "cost_basis": cb,
            "current_price": round(curr_price, 2),
            "market_value": mkt_val,
            "unrealized_pnl": round(mkt_val - cost_val, 2),
        })

    return {
        "status": "success",
        "action": action,
        "total_portfolio_value": round(total_market_val, 2),
        "total_cost_basis": round(total_cost, 2),
        "total_unrealized_pnl": round(total_market_val - total_cost, 2),
        "holdings": holdings_summary,
    }


def calculate_asset_allocation(
    symbols: list[str],
    total_capital: float,
    strategy: str = "equal",
) -> dict:
    """Calculates target capital allocation across a basket of stock symbols.

    Args:
        symbols: List of stock symbols to allocate across.
        total_capital: Total amount of capital in USD.
        strategy: 'equal', 'market_cap', or 'low_risk'.
    """
    if not symbols or total_capital <= 0:
        return {"error": "Requires at least one symbol and positive total_capital."}

    symbols = [s.strip().upper() for s in symbols]
    allocations = []
    prices = {}
    market_caps = {}
    betas = {}

    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            prices[sym] = float(ticker.fast_info.get("last_price", 100.0))
            market_caps[sym] = float(ticker.fast_info.get("market_cap") or ticker.info.get("marketCap", 1e9))
            betas[sym] = float(ticker.info.get("beta", 1.0)) if ticker.info.get("beta") else 1.0
        except Exception:
            prices[sym] = 100.0
            market_caps[sym] = 1e9
            betas[sym] = 1.0

    if strategy == "market_cap":
        total_mcap = sum(market_caps.values())
        weights = {s: market_caps[s] / total_mcap for s in symbols}
    elif strategy == "low_risk":
        inv_betas = {s: (1.0 / max(betas[s], 0.2)) for s in symbols}
        total_inv = sum(inv_betas.values())
        weights = {s: inv_betas[s] / total_inv for s in symbols}
    else:
        eq = 1.0 / len(symbols)
        weights = {s: eq for s in symbols}

    for sym in symbols:
        w = weights[sym]
        allocated = round(total_capital * w, 2)
        pr = prices[sym]
        shares = round(allocated / pr, 2) if pr > 0 else 0
        allocations.append({
            "symbol": sym,
            "target_weight": f"{round(w * 100, 2)}%",
            "allocated_dollars": allocated,
            "current_price": round(pr, 2),
            "target_shares": shares,
            "beta": round(betas[sym], 2),
        })

    return {
        "strategy": strategy,
        "total_capital": total_capital,
        "symbols_count": len(symbols),
        "allocations": allocations,
    }


def get_company_news(symbol: str, max_articles: int = 5) -> list[dict]:
    """Retrieves recent breaking news headlines, summaries, and publishers for a company.

    Args:
        symbol: The stock ticker symbol.
        max_articles: Maximum number of articles.
    """
    symbol = symbol.strip().upper()
    try:
        raw_news = yf.Ticker(symbol).news or []
        articles = []
        for item in raw_news[:max_articles]:
            content = item.get("content", item)
            title = content.get("title") or item.get("title")
            summary = content.get("summary") or item.get("summary") or ""
            publisher = (content.get("provider", {}) or {}).get("displayName") or item.get("publisher")
            url = (content.get("canonicalUrl", {}) or {}).get("url") or item.get("link")
            articles.append({
                "symbol": symbol,
                "title": title,
                "publisher": publisher,
                "summary": summary[:300] + "..." if len(summary) > 300 else summary,
                "url": url,
            })
        return articles if articles else [{"message": f"No recent news found for {symbol}."}]
    except Exception as e:
        return [{"error": f"Failed to retrieve news for {symbol}: {str(e)}"}]


ANTIGRAVITY_FINANCE_TOOLS = [
    get_stock_quote,
    get_historical_performance,
    get_financial_metrics,
    manage_portfolio,
    calculate_asset_allocation,
    get_company_news,
]

