"""
tools/tradingview.py - TradingView Integration Engine
Generates embeddable, responsive TradingView widgets for Streamlit:
1. Advanced Real-Time Interactive Candlestick Charts (drawing tools, indicators, live quotes)
2. Technical Analysis Speedometer / Consensus Gauge (Oscillators & Moving Averages)
3. Fundamental Financials & Valuation Ratios
4. Company Profile & Market Overview
"""

import subprocess
import os
from typing import Optional


def launch_tradingview_desktop() -> bool:
    """Launch installed TradingView Desktop application on Windows."""
    try:
        subprocess.Popen(["explorer.exe", "shell:AppsFolder\\TradingView.Desktop_n534cwy3pjxzj!TradingView.Desktop"])
        return True
    except Exception:
        return False


def get_tradingview_web_url(symbol: str) -> str:
    """Generate official TradingView web chart URL for any global symbol."""
    tv_symbol = format_tradingview_symbol(symbol)
    return f"https://www.tradingview.com/chart/?symbol={tv_symbol}"



def format_tradingview_symbol(ticker: str) -> str:
    """
    Format any ticker symbol into a TradingView-compatible symbol format.
    Handles US equities, Indian NSE/BSE, UK LSE, European exchanges, and Crypto.
    """
    clean = (ticker or "").strip().upper()
    if not clean:
        return "NASDAQ:AAPL"

    if clean.endswith(".NS"):
        return f"NSE:{clean[:-3]}"
    elif clean.endswith(".BO"):
        return f"BSE:{clean[:-3]}"
    elif clean.endswith(".L"):
        return f"LSE:{clean[:-2]}"
    elif clean.endswith(".DE"):
        return f"XETR:{clean[:-3]}"
    elif clean.endswith(".PA"):
        return f"EURONEXT:{clean[:-3]}"
    elif clean.endswith(".TO"):
        return f"TSX:{clean[:-3]}"
    elif clean.endswith(".AX"):
        return f"ASX:{clean[:-3]}"
    elif clean.endswith(".T"):
        return f"TSE:{clean[:-2]}"
    elif clean == "BTC-USD":
        return "BINANCE:BTCUSDT"
    elif clean == "ETH-USD":
        return "BINANCE:ETHUSDT"

    # Default US & general symbol
    return clean


def render_tradingview_advanced_chart(
    symbol: str,
    theme: str = "light",
    interval: str = "D",
    height: int = 650
) -> str:
    """
    Generate responsive TradingView Advanced Real-Time Chart widget HTML.
    Includes full institutional indicator suite, drawing tools, and live market quotes.
    """
    tv_symbol = format_tradingview_symbol(symbol)
    theme_val = "dark" if theme.lower() == "dark" else "light"

    html = f"""
    <div class="tradingview-widget-container" style="height:{height}px;width:100%;">
      <div id="tradingview_chart_widget" style="height:calc(100% - 32px);width:100%;"></div>
      <div class="tradingview-widget-copyright" style="font-size:12px;color:#888;padding:4px 0;">
        <a href="https://www.tradingview.com/symbols/{tv_symbol}/" rel="noopener noreferrer" target="_blank" style="color:#2962FF;text-decoration:none;">
          <span style="color:#2962FF;">{tv_symbol} Chart</span>
        </a> by TradingView
      </div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "{interval}",
        "timezone": "Etc/UTC",
        "theme": "{theme_val}",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart_widget",
        "hide_side_toolbar": false,
        "withdateranges": true,
        "studies": [
          "STD;SMA",
          "STD;RSI",
          "STD;MACD"
        ]
      }}
      );
      </script>
    </div>
    """
    return html


def render_tradingview_technical_analysis(
    symbol: str,
    theme: str = "light",
    interval: str = "1D",
    height: int = 460
) -> str:
    """
    Generate TradingView Technical Analysis Speedometer / Consensus Gauge widget HTML.
    Aggregates 26 technical indicators across Oscillators and Moving Averages.
    """
    tv_symbol = format_tradingview_symbol(symbol)
    theme_val = "dark" if theme.lower() == "dark" else "light"

    html = f"""
    <div class="tradingview-widget-container" style="height:{height}px;width:100%;">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
      {{
        "interval": "{interval}",
        "width": "100%",
        "isTransparent": false,
        "height": "{height}",
        "symbol": "{tv_symbol}",
        "showIntervalTabs": true,
        "displayMode": "single",
        "locale": "en",
        "colorTheme": "{theme_val}"
      }}
      </script>
    </div>
    """
    return html


def render_tradingview_financials(
    symbol: str,
    theme: str = "light",
    height: int = 550
) -> str:
    """
    Generate TradingView Financials & Valuation Multiples widget HTML.
    Displays Income Statement, Balance Sheet, and Cash Flow statements.
    """
    tv_symbol = format_tradingview_symbol(symbol)
    theme_val = "dark" if theme.lower() == "dark" else "light"

    html = f"""
    <div class="tradingview-widget-container" style="height:{height}px;width:100%;">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-financials.js" async>
      {{
        "isTransparent": false,
        "largeChartUrl": "",
        "displayMode": "regular",
        "width": "100%",
        "height": "{height}",
        "colorTheme": "{theme_val}",
        "symbol": "{tv_symbol}",
        "locale": "en"
      }}
      </script>
    </div>
    """
    return html


def render_tradingview_company_profile(
    symbol: str,
    theme: str = "light",
    height: int = 400
) -> str:
    """
    Generate TradingView Company Profile widget HTML.
    Shows company description, sector, industry, and corporate overview.
    """
    tv_symbol = format_tradingview_symbol(symbol)
    theme_val = "dark" if theme.lower() == "dark" else "light"

    html = f"""
    <div class="tradingview-widget-container" style="height:{height}px;width:100%;">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-profile.js" async>
      {{
        "width": "100%",
        "height": "{height}",
        "colorTheme": "{theme_val}",
        "isTransparent": false,
        "symbol": "{tv_symbol}",
        "locale": "en"
      }}
      </script>
    </div>
    """
    return html
