"""
tests/test_tradingview.py - Unit tests for TradingView integration
"""

import pytest
from tools.tradingview import (
    format_tradingview_symbol,
    render_tradingview_advanced_chart,
    render_tradingview_technical_analysis,
    render_tradingview_financials,
    render_tradingview_company_profile,
    get_tradingview_web_url
)


def test_format_tradingview_symbol():
    assert format_tradingview_symbol("AAPL") == "AAPL"
    assert format_tradingview_symbol("TCS.NS") == "NSE:TCS"
    assert format_tradingview_symbol("RELIANCE.NS") == "NSE:RELIANCE"
    assert format_tradingview_symbol("TCS.BO") == "BSE:TCS"
    assert format_tradingview_symbol("SHEL.L") == "LSE:SHEL"
    assert format_tradingview_symbol("SAP.DE") == "XETR:SAP"
    assert format_tradingview_symbol("BTC-USD") == "BINANCE:BTCUSDT"
    assert format_tradingview_symbol("") == "NASDAQ:AAPL"


def test_render_widgets():
    chart_html = render_tradingview_advanced_chart("NVDA", theme="dark", height=600)
    assert "NVDA" in chart_html
    assert "TradingView.widget" in chart_html
    assert "dark" in chart_html

    ta_html = render_tradingview_technical_analysis("TSLA", theme="light")
    assert "TSLA" in ta_html
    assert "embed-widget-technical-analysis.js" in ta_html

    fin_html = render_tradingview_financials("MSFT")
    assert "MSFT" in fin_html
    assert "embed-widget-financials.js" in fin_html

    prof_html = render_tradingview_company_profile("AAPL")
    assert "AAPL" in prof_html
    assert "embed-widget-symbol-profile.js" in prof_html


def test_get_tradingview_web_url():
    url = get_tradingview_web_url("TCS.NS")
    assert url == "https://www.tradingview.com/chart/?symbol=NSE:TCS"
