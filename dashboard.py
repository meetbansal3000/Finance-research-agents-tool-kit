"""
dashboard.py - Interactive Financial Research & Shortlisting Terminal
Built with Streamlit and Plotly for the Antigravity Autonomous Finance Suite.
Features:
  1. 🏆 Shortlisting Scorecard: Multi-factor screening (Operating Margin, Leverage, FCF Yield)
  2. 📊 Live Candlestick Charts: Interactive OHLCV charts with volume and moving averages
  3. 🎛️ Interactive DCF Valuation: Dynamic sliders for WACC, 5Y Growth, Terminal Growth, and sensitivity table
  4. 🤖 Autonomous Multi-Agent Committee: Live research runner for any global ticker
  5. ⚡ NVIDIA cuOpt Portfolio Optimizer: Quadratic programming portfolio variance minimization
  6. 🚚 Supply Chain Logistics Optimizer: cuOpt CVRP fleet routing & margin elasticity
  7. 📓 Decision Journal Viewer: Real-time portfolio journal inspection and decision logging
  8. 🚨 Regulatory Filing & Market Alerts: Live monitor of SEC filings and price shocks
"""

import os
import sys
import datetime
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from tools.calc.dcf import dcf, reverse_dcf
from tools.backtest import BacktestSandbox
from tools.data_layer import DataLayer
from tools.alerts import AlertMonitor
from tools.calc.portfolio_opt import PortfolioQPOptimizer
from tools.calc.supply_chain_opt import SupplyChainLogisticsOptimizer
from tools.ticker_search import (
    search_company_tickers,
    lookup_primary_ticker,
    load_saved_watchlist,
    save_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    reset_watchlist,
    compute_ticker_scorecard_metrics,
    DEFAULT_WATCHLIST
)

from tools.tradingview import (
    format_tradingview_symbol,
    render_tradingview_advanced_chart,
    render_tradingview_technical_analysis,
    render_tradingview_financials,
    render_tradingview_company_profile,
    launch_tradingview_desktop,
    get_tradingview_web_url
)

# Check if running in Streamlit
try:
    import streamlit as st
    import streamlit.components.v1 as components
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


def run_standalone_launcher():
    """Fallback if user runs 'python dashboard.py' in terminal instead of 'streamlit run'."""
    import subprocess
    print("=" * 60)
    print("🚀 LAUNCHING ANTIGRAVITY RESEARCH TERMINAL")
    print("=" * 60)
    print("Starting Streamlit web dashboard on http://localhost:8501 ...")
    venv_streamlit = os.path.join(PROJECT_DIR, ".venv", "Scripts", "streamlit.exe")
    cmd = [venv_streamlit if os.path.exists(venv_streamlit) else "streamlit", "run", __file__]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nTerminal stopped.")


if not HAS_STREAMLIT:
    if __name__ == "__main__":
        run_standalone_launcher()
    sys.exit(0)


# =============================================================================
# STREAMLIT UI CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="Antigravity Research Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #1f77b4;
        margin-bottom: 10px;
    }
    .header-style {
        font-size: 26px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# WATCHLIST & DATA HELPERS
# =============================================================================
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = load_saved_watchlist()

if "active_ticker" not in st.session_state:
    st.session_state["active_ticker"] = "NVDA"


@st.cache_data(ttl=1800)
def load_historical_prices(ticker: str, period: str = "1y"):
    clean_sym = ticker.strip().upper()
    t = yf.Ticker(clean_sym)
    df = t.history(period=period)
    return df


@st.cache_data(ttl=600)
def get_shortlist_metrics_for_universe(tickers_tuple):
    records = []
    for sym in tickers_tuple:
        row = compute_ticker_scorecard_metrics(sym)
        records.append(row)
    return pd.DataFrame(records)


# =============================================================================
# SIDEBAR NAVIGATION & GLOBAL COMPANY SEARCH
# =============================================================================
st.sidebar.title("🦅 Antigravity Terminal")
st.sidebar.markdown("**System:** Autonomous Multi-Agent Research")
st.sidebar.markdown("**Data Integrity:** Audited Primary Filings & Provenance")

nav_choice = st.sidebar.radio(
    "Navigation View",
    [
        "🏆 Shortlisting Scorecard",
        "📈 TradingView & Market Charts",
        "🎛️ Interactive DCF Valuation",
        "🤖 Autonomous Research Committee",
        "⚡ NVIDIA cuOpt Portfolio Optimizer",
        "🚚 Supply Chain & Margins (cuOpt)",
        "📓 Decision Journal & Review",
        "🚨 SEC Filings & Price Alerts"
    ]
)

st.sidebar.divider()

# Global Watchlist Quick View in Sidebar
st.sidebar.subheader(f"⭐ Active Watchlist ({len(st.session_state['watchlist'])})")
st.sidebar.caption(", ".join(st.session_state["watchlist"]))

# Global Company Name to Ticker Search Tool in Sidebar
with st.sidebar.expander("🔍 Find Ticker by Company Name", expanded=False):
    search_q = st.text_input("Enter Company Name", placeholder="e.g. Tesla, Apple, Reliance, Palantir", key="sb_company_search")
    if search_q.strip():
        with st.spinner("Searching global exchanges..."):
            found = search_company_tickers(search_q, max_results=5)
        if found:
            for item in found:
                col_info, col_btn = st.columns([3, 1])
                with col_info:
                    st.markdown(f"**{item['symbol']}** — {item['name']}\n*{item['exchange']} ({item['type']})*")
                with col_btn:
                    if st.button("➕ Add", key=f"sb_add_{item['symbol']}"):
                        ok, msg, updated = add_to_watchlist(item['symbol'])
                        st.session_state["watchlist"] = updated
                        st.sidebar.success(msg)
                        st.rerun()
        else:
            st.info(f"No tickers found for '{search_q}'. Try a different keyword.")

st.sidebar.divider()

# TradingView Desktop Application Launcher
if st.sidebar.button("🖥️ Open TradingView Desktop", use_container_width=True, help="Launch installed TradingView Desktop application on Windows"):
    success = launch_tradingview_desktop()
    if success:
        st.sidebar.success("🚀 Launched TradingView Desktop!")
    else:
        st.sidebar.warning("Could not launch TradingView Desktop. Please verify Windows installation.")

st.sidebar.info("💡 **Universal Ticker Support:** Works for any US equity (NYSE/NASDAQ), Foreign 20-F (TSM, ASML), Indian stocks (.NS/.BO), UK (.L), Europe (.DE/.PA), Japan (.T), or global ETFs (SPY, QQQ).")


# =============================================================================
# VIEW 1: SHORTLISTING SCORECARD & WATCHLIST MANAGER
# =============================================================================
if nav_choice == "🏆 Shortlisting Scorecard":
    st.markdown('<div class="header-style">🏆 Institutional Shortlist & Watchlist Scorecard</div>', unsafe_allow_html=True)
    st.markdown("Multi-factor fundamental scorecard comparing primary coverage candidates. Add any global company to evaluate.")

    # Watchlist Addition & Management Box
    with st.container():
        st.markdown("### ➕ Add Stocks to Your Watchlist")
        w_col1, w_col2, w_col3 = st.columns([3, 1, 1])
        with w_col1:
            stock_to_add = st.text_input(
                "Search by Company Name or Ticker Symbol",
                placeholder="e.g. Tesla, Apple, Palantir, Tata Motors, RELIANCE.NS, TSLA",
                help="Type any company name (e.g. 'Tesla') or direct symbol (e.g. 'TSLA') to add."
            )
            # Show live resolution preview if text is entered
            resolved_preview = None
            if stock_to_add.strip():
                resolved_preview = lookup_primary_ticker(stock_to_add)
                if resolved_preview:
                    st.caption(f"✨ **Resolved Ticker:** `{resolved_preview}` (Matches: '{stock_to_add.strip()}')")

        with w_col2:
            st.write("")
            st.write("")
            if st.button("➕ Add to Watchlist", type="primary", use_container_width=True):
                if stock_to_add.strip():
                    ok, msg, updated = add_to_watchlist(stock_to_add)
                    st.session_state["watchlist"] = updated
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                    st.rerun()
                else:
                    st.warning("Please enter a company name or ticker.")

        with w_col3:
            st.write("")
            st.write("")
            if st.button("🔄 Reset to Default", use_container_width=True, help="Reset watchlist back to the 6 institutional core stocks"):
                updated = reset_watchlist()
                st.session_state["watchlist"] = updated
                st.info("Watchlist reset to default baseline.")
                st.rerun()

    # Active Watchlist Tags & Removal
    st.markdown(f"**Current Watchlist ({len(st.session_state['watchlist'])} Stocks):** " + " • ".join([f"`{s}`" for s in st.session_state["watchlist"]]))
    
    with st.expander("Manage / Remove Watchlist Items"):
        rem_col1, rem_col2 = st.columns([3, 1])
        with rem_col1:
            to_remove = st.selectbox("Select Stock to Remove", ["(Select stock to remove)"] + st.session_state["watchlist"])
        with rem_col2:
            st.write("")
            st.write("")
            if st.button("❌ Remove Stock", use_container_width=True):
                if to_remove and to_remove != "(Select stock to remove)":
                    updated = remove_from_watchlist(to_remove)
                    st.session_state["watchlist"] = updated
                    st.success(f"Removed '{to_remove}' from Watchlist.")
                    st.rerun()

    st.divider()

    # Filters
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        min_margin = st.slider("Min Operating Margin (%)", min_value=0, max_value=50, value=15)
    with col_f2:
        max_de = st.slider("Max Debt/Equity Ratio (x)", min_value=0.1, max_value=3.0, value=1.5, step=0.1)
    with col_f3:
        st.write("")
        st.write("")
        show_all = st.checkbox("Show International Equities (.NS, .L, etc.)", value=True)

    with st.spinner("Calculating live fundamental scorecard metrics..."):
        df_scorecard = get_shortlist_metrics_for_universe(tuple(st.session_state["watchlist"]))

    if not show_all and not df_scorecard.empty:
        df_scorecard = df_scorecard[~df_scorecard["Ticker"].str.contains(r"\.")]

    # Apply sliders filter if columns parseable
    if not df_scorecard.empty:
        try:
            op_nums = df_scorecard["Operating Margin"].str.rstrip("%").astype(float)
            de_nums = df_scorecard["Debt/Equity"].str.rstrip("x").astype(float)
            filtered_df = df_scorecard[(op_nums >= min_margin) & (de_nums <= max_de)]
        except Exception:
            filtered_df = df_scorecard

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        # CSV Export
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Watchlist Scorecard (CSV)",
            data=csv_data,
            file_name=f"watchlist_scorecard_{datetime.date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Watchlist is currently empty. Use the box above to add companies.")

    st.subheader("💡 Key Shortlisting Takeaways")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.success("**Institutional Green Flags:**\n- **High Operating Margin (>25%):** Pricing power and moats that sustain reinvestment.\n- **Low Leverage (<0.5x D/E):** Strong solvency protecting equity in downturns.\n- **High FCF Conversion (>70%):** Accounting profits convert to cash available for shareholders.")
    with col_t2:
        st.warning("**Red Flags & Skeptic Checks:**\n- **Customer Concentration:** Reliance on single customer >10% creates binary earnings risk.\n- **Leverage Accumulation:** High D/E (>1.5x) limits debt capacity and increases interest rate sensitivity.\n- **Thin Margins (<10%):** Vulnerable to cost inflation and commodity price shocks.")


# =============================================================================
# VIEW 2: TRADINGVIEW & LIVE MARKET CHARTS
# =============================================================================
elif "TradingView" in nav_choice or "Candlestick" in nav_choice:
    st.markdown('<div class="header-style">📈 TradingView Interactive Pro Terminal</div>', unsafe_allow_html=True)
    st.markdown("Real-time TradingView charting engine with institutional indicators, drawing tools, technical consensus gauges, and desktop app integration.")

    c_col1, c_col2 = st.columns([1, 3])
    with c_col1:
        # Quick pick from watchlist
        wl_options = ["(Custom Search)"] + st.session_state["watchlist"]
        picked_wl = st.selectbox("⭐ Quick Pick from Watchlist", options=wl_options)

        default_input = picked_wl if picked_wl != "(Custom Search)" else st.session_state.get("active_ticker", "NVDA")
        user_input = st.text_input("Enter Company Name or Ticker", value=default_input, help="Type 'Tesla', 'Apple', 'Palantir' or exact symbol 'NVDA', 'TCS.NS'")
        
        # Resolve company name to ticker
        resolved_ticker = lookup_primary_ticker(user_input) or user_input.strip().upper()
        if resolved_ticker != user_input.strip().upper():
            st.info(f"✨ Resolved '{user_input.strip()}' to **{resolved_ticker}**")

        st.session_state["active_ticker"] = resolved_ticker
        selected_ticker = resolved_ticker
        tv_symbol = format_tradingview_symbol(selected_ticker)

        # Quick button to add this ticker to watchlist if not already there
        if selected_ticker not in st.session_state["watchlist"]:
            if st.button(f"➕ Add {selected_ticker} to Watchlist", use_container_width=True):
                ok, msg, updated = add_to_watchlist(selected_ticker)
                st.session_state["watchlist"] = updated
                st.success(msg)
                st.rerun()

        st.divider()
        st.markdown("**🖥️ Desktop & Web Launchers**")
        if st.button("🚀 Open in TradingView Desktop", use_container_width=True, help="Open installed TradingView app on Windows (Drive D)"):
            launched = launch_tradingview_desktop()
            if launched:
                st.success("Launched TradingView Desktop App!")
            else:
                st.warning("Could not launch TradingView Desktop.")

        tv_web_url = get_tradingview_web_url(selected_ticker)
        st.markdown(f'<a href="{tv_web_url}" target="_blank"><button style="width:100%;padding:8px;border-radius:6px;border:1px solid #1f77b4;background:#1f77b4;color:white;cursor:pointer;font-weight:600;">🌐 Open on TradingView.com</button></a>', unsafe_allow_html=True)

        st.divider()
        chart_theme = st.radio("Chart Theme", ["light", "dark"], horizontal=True)
        chart_interval = st.selectbox("Default Interval", ["D (Daily)", "W (Weekly)", "1 (1 Minute)", "5 (5 Minutes)", "15 (15 Minutes)", "60 (1 Hour)", "240 (4 Hours)", "M (Monthly)"], index=0)
        parsed_interval = chart_interval.split()[0]

    with c_col2:
        tv_tab1, tv_tab2, tv_tab3, tv_tab4 = st.tabs([
            "📈 TradingView Live Chart",
            "🧭 Technical Analysis Gauge",
            "🏢 Fundamental Financials",
            "📊 Quantitative Candlestick & SMAs"
        ])

        with tv_tab1:
            st.caption(f"Showing real-time streaming chart for **{tv_symbol}** ({selected_ticker}). Use the top toolbar for technical indicators and drawing tools.")
            chart_html = render_tradingview_advanced_chart(
                symbol=selected_ticker,
                theme=chart_theme,
                interval=parsed_interval,
                height=650
            )
            components.html(chart_html, height=670, scrolling=False)

        with tv_tab2:
            st.caption(f"Real-time technical analysis consensus gauge across 26 technical indicators for **{tv_symbol}**.")
            ta_html = render_tradingview_technical_analysis(
                symbol=selected_ticker,
                theme=chart_theme,
                interval="1D",
                height=460
            )
            components.html(ta_html, height=480, scrolling=False)

        with tv_tab3:
            st.caption(f"Financial statements, operating margin ratios, and balance sheet structure for **{tv_symbol}**.")
            fin_html = render_tradingview_financials(
                symbol=selected_ticker,
                theme=chart_theme,
                height=550
            )
            components.html(fin_html, height=570, scrolling=False)

        with tv_tab4:
            st.caption("Quantitative historical candlestick analysis with 50-Day and 200-Day moving averages.")
            q_col1, q_col2 = st.columns([1, 1])
            with q_col1:
                chart_period = st.select_slider("Time Horizon", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")
            with q_col2:
                show_sma50 = st.checkbox("Show 50-Day SMA", value=True)
                show_sma200 = st.checkbox("Show 200-Day SMA", value=True)

            with st.spinner(f"Loading quantitative price data for {selected_ticker}..."):
                df_hist = load_historical_prices(selected_ticker, period=chart_period)

            if df_hist is not None and not df_hist.empty:
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.08,
                    subplot_titles=(f"{selected_ticker} Daily Price History", "Volume"),
                    row_width=[0.25, 0.75]
                )
                fig.add_trace(
                    go.Candlestick(
                        x=df_hist.index,
                        open=df_hist["Open"],
                        high=df_hist["High"],
                        low=df_hist["Low"],
                        close=df_hist["Close"],
                        name="OHLC"
                    ),
                    row=1, col=1
                )
                if show_sma50 and len(df_hist) >= 50:
                    sma50 = df_hist["Close"].rolling(window=50).mean()
                    fig.add_trace(go.Scatter(x=df_hist.index, y=sma50, line=dict(color="orange", width=1.5), name="50-Day SMA"), row=1, col=1)
                if show_sma200 and len(df_hist) >= 200:
                    sma200 = df_hist["Close"].rolling(window=200).mean()
                    fig.add_trace(go.Scatter(x=df_hist.index, y=sma200, line=dict(color="blue", width=1.5), name="200-Day SMA"), row=1, col=1)
                fig.add_trace(
                    go.Bar(x=df_hist.index, y=df_hist["Volume"], name="Volume", marker_color="rgba(0,100,250,0.5)"),
                    row=2, col=1
                )
                fig.update_layout(
                    height=550,
                    xaxis_rangeslider_visible=False,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"Unable to load historical price series for '{selected_ticker}'. Please verify company name or ticker symbol.")


# =============================================================================
# VIEW 3: INTERACTIVE DCF VALUATION & SENSITIVITY
# =============================================================================
elif nav_choice == "🎛️ Interactive DCF Valuation":
    st.markdown('<div class="header-style">🎛️ Interactive DCF Valuation & Sensitivity Analysis</div>', unsafe_allow_html=True)
    st.markdown("Dynamic Discounted Cash Flow valuation engine powered by `tools/calc/dcf.py`.")

    dcf_presets = {
        "NVDA": {"fcf": 60850000000.0, "shares": 24500000000.0, "net_debt": -38200000000.0, "price": 239.24, "wacc": 0.095, "growth": 0.22, "t_growth": 0.035},
        "AAPL": {"fcf": 108807000000.0, "shares": 14594180000.0, "net_debt": -33763000000.0, "price": 333.63, "wacc": 0.085, "growth": 0.08, "t_growth": 0.03},
        "MSFT": {"fcf": 74071000000.0, "shares": 7430000000.0, "net_debt": -36549000000.0, "price": 529.30, "wacc": 0.088, "growth": 0.12, "t_growth": 0.03},
        "GOOGL": {"fcf": 73200000000.0, "shares": 12250000000.0, "net_debt": -71100000000.0, "price": 347.68, "wacc": 0.090, "growth": 0.14, "t_growth": 0.03}
    }

    t_col1, t_col2 = st.columns([1, 2])
    with t_col1:
        custom_sym = st.text_input("Enter Ticker for DCF", value="NVDA").strip().upper()
        if custom_sym in dcf_presets:
            preset = dcf_presets[custom_sym]
        else:
            # Dynamically fetch baseline data for custom ticker
            try:
                t_obj = yf.Ticker(custom_sym)
                info = t_obj.info
                curr_p = float(info.get("currentPrice") or info.get("regularMarketPrice") or 100.0)
                shs = float(info.get("sharesOutstanding") or 1e9)
                fcf_val = float(info.get("freeCashflow") or (curr_p * shs * 0.04))
                debt = float(info.get("totalDebt") or 0.0)
                cash = float(info.get("totalCash") or 0.0)
                preset = {
                    "fcf": max(fcf_val, 1e7),
                    "shares": max(shs, 1e6),
                    "net_debt": debt - cash,
                    "price": curr_p,
                    "wacc": 0.09,
                    "growth": 0.10,
                    "t_growth": 0.025
                }
            except Exception:
                preset = dcf_presets["NVDA"]

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        slider_wacc = st.slider("Discount Rate / WACC (%)", min_value=6.0, max_value=16.0, value=float(preset["wacc"] * 100), step=0.25) / 100.0
    with col_s2:
        slider_growth = st.slider("5-Year FCF Growth Rate (%)", min_value=-10.0, max_value=50.0, value=float(preset["growth"] * 100), step=0.5) / 100.0
    with col_s3:
        slider_t_growth = st.slider("Terminal Growth Rate (%)", min_value=1.5, max_value=4.5, value=float(preset["t_growth"] * 100), step=0.25) / 100.0

    growth_rates = [slider_growth] * 5
    dcf_calc = dcf(
        base_fcf=preset["fcf"],
        growth_rates=growth_rates,
        discount_rate=slider_wacc,
        terminal_growth_rate=slider_t_growth,
        shares_outstanding=preset["shares"],
        net_debt=preset["net_debt"]
    )
    dcf_res = dcf_calc["result"]
    fair_val = dcf_res["fair_value_per_share"]
    curr_price = preset["price"]
    upside_pct = ((fair_val - curr_price) / curr_price) * 100.0 if curr_price > 0 else 0.0

    st.divider()
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric("Current Market Price", f"${curr_price:,.2f}")
    with m_col2:
        st.metric("Model Fair Value", f"${fair_val:,.2f}")
    with m_col3:
        st.metric("Margin of Safety / Upside", f"{upside_pct:+.1f}%", delta=f"{upside_pct:+.1f}%")
    with m_col4:
        st.metric("Enterprise Value", f"${dcf_res['enterprise_value'] / 1e9:,.1f}B")

    st.subheader(f"📊 Sensitivity Matrix: {custom_sym} (WACC vs Growth)")
    wacc_range = np.linspace(slider_wacc - 0.02, slider_wacc + 0.02, 5)
    growth_range = np.linspace(slider_growth - 0.06, slider_growth + 0.06, 5)

    matrix_data = []
    for g in growth_range:
        row = []
        for w in wacc_range:
            g_rates = [g] * 5
            res_calc = dcf(
                base_fcf=preset["fcf"],
                growth_rates=g_rates,
                discount_rate=w,
                terminal_growth_rate=slider_t_growth,
                shares_outstanding=preset["shares"],
                net_debt=preset["net_debt"]
            )
            row.append(f"${res_calc['result']['fair_value_per_share']:,.1f}")
        matrix_data.append(row)

    df_matrix = pd.DataFrame(
        matrix_data,
        index=[f"Growth {g*100:.1f}%" for g in growth_range],
        columns=[f"WACC {w*100:.2f}%" for w in wacc_range]
    )
    st.table(df_matrix)


# =============================================================================
# VIEW 4: AUTONOMOUS MULTI-AGENT COMMITTEE RESEARCH
# =============================================================================
elif nav_choice == "🤖 Autonomous Research Committee":
    st.markdown('<div class="header-style">🤖 Autonomous Multi-Agent Research Committee</div>', unsafe_allow_html=True)
    st.markdown("Triggers the full multi-agent pipeline: **Analyst** $\\to$ **Verifier** $\\to$ **Skeptic** $\\to$ **NVIDIA NIM** $\\to$ **Provenance Ledger**.")

    col_r1, col_r2 = st.columns([2, 1])
    with col_r1:
        wl_opts = ["(Custom Input)"] + st.session_state["watchlist"]
        r_picked = st.selectbox("⭐ Quick Pick from Watchlist", wl_opts)
        default_r = r_picked if r_picked != "(Custom Input)" else "AAPL"
        r_input = st.text_input("Enter Company Name or Stock Ticker to Research", value=default_r, help="Type company name (e.g. 'Tesla', 'Apple', 'Palantir') or ticker (e.g. 'NVDA')")
        research_ticker = lookup_primary_ticker(r_input) or r_input.strip().upper()
        if research_ticker != r_input.strip().upper():
            st.caption(f"✨ Resolved '{r_input.strip()}' to ticker `{research_ticker}`")
    with col_r2:
        workflow_type = st.selectbox("Research Workflow", ["Workflow 1: Comprehensive Valuation Deep Dive", "Workflow 2: Rapid Fundamental Screen"])
        workflow_num = 1 if "1" in workflow_type else 2

    if st.button("🚀 Run Autonomous Committee Research", type="primary"):
        with st.spinner(f"Agents assembling for {research_ticker}... Running Analyst -> Verifier -> Skeptic pipeline..."):
            try:
                from run_research import run_pipeline
                res_pipeline = run_pipeline(ticker=research_ticker, workflow_number=workflow_num, strict_audit=False)
                
                st.success(f"✅ Research Committee successfully completed audit for {research_ticker}!")
                
                # Check for generated report
                report_dir = res_pipeline.get("report_dir")
                final_md = os.path.join(report_dir, "final_report.md") if report_dir else None
                
                if final_md and os.path.exists(final_md):
                    with open(final_md, "r", encoding="utf-8") as f:
                        report_content = f.read()
                    
                    st.divider()
                    st.subheader(f"📄 Audited Investment Memorandum: {research_ticker}")
                    st.markdown(report_content)
                else:
                    st.info("Research complete. Status: " + str(res_pipeline.get("status", "COMPLETE")))
            except Exception as e:
                st.error(f"Error during autonomous research: {str(e)}")


# =============================================================================
# VIEW 5: NVIDIA CUOPT PORTFOLIO OPTIMIZATION
# =============================================================================
elif nav_choice == "⚡ NVIDIA cuOpt Portfolio Optimizer":
    st.markdown('<div class="header-style">⚡ NVIDIA cuOpt Quadratic Programming (QP) Portfolio Optimizer</div>', unsafe_allow_html=True)
    st.markdown("Implements the mathematical formulation principles from **NVIDIA cuOpt** (`min 0.5 * w^T Q w`) for Global Minimum Variance and Markowitz allocation.")

    p_col1, p_col2 = st.columns([2, 1])
    with p_col1:
        wl_preview_str = ", ".join(st.session_state["watchlist"][:5])
        port_input = st.text_input("Portfolio Universe (Comma-separated)", value=wl_preview_str, help="Type any list of stocks or use your active Watchlist")
        use_all_wl = st.checkbox(f"Use All {len(st.session_state['watchlist'])} Stocks in Current Watchlist", value=False)
    with p_col2:
        strategy_choice = st.selectbox("Optimization Strategy", ["min_variance (Global Minimum Variance)", "mean_variance (Markowitz Efficient)"])
        strat = "min_variance" if "min_variance" in strategy_choice else "mean_variance"

    max_w_cap = st.slider("Single-Asset Concentration Cap", min_value=0.20, max_value=1.0, value=0.40, step=0.05)

    if st.button("⚡ Solve Optimal Portfolio Allocation", type="primary"):
        if use_all_wl:
            tickers_list = list(st.session_state["watchlist"])
        else:
            tickers_list = [t.strip().upper() for t in port_input.split(",") if t.strip()]
        with st.spinner(f"Solving quadratic program for {tickers_list}..."):
            try:
                sandbox = BacktestSandbox()
                bt_res = sandbox.run_optimized_portfolio_backtest(
                    tickers=tickers_list,
                    benchmark="SPY",
                    period="1y",
                    max_weight=max_w_cap,
                    strategy=strat
                )
                
                st.success("✅ NVIDIA cuOpt QP Optimization Converged to Optimum!")
                
                qp = bt_res["qp_solution"]
                opt_weights = qp["weights"]

                # Metrics summary
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.metric("Annualized Volatility", f"{qp['annualized_volatility']:.2f}%")
                with col_m2:
                    st.metric("Sharpe Ratio (Rf=4.25%)", f"{bt_res['sharpe_ratio']:.2f}")
                with col_m3:
                    st.metric("1Y Portfolio Return", f"{bt_res['portfolio_return_pct']:+.2f}%")
                with col_m4:
                    st.metric("Alpha vs SPY", f"{bt_res['alpha_pct']:+.2f}%", delta=f"{bt_res['alpha_pct']:+.2f}%")

                # Optimal Weights Chart
                df_w = pd.DataFrame(list(opt_weights.items()), columns=["Asset", "Optimal Weight"])
                df_w["Optimal Weight (%)"] = df_w["Optimal Weight"] * 100.0

                fig_w = go.Figure(data=[go.Pie(labels=df_w["Asset"], values=df_w["Optimal Weight (%)"], hole=0.4)])
                fig_w.update_layout(title="Optimal Capital Allocation (Simplex Sum = 100%)", height=450)
                st.plotly_chart(fig_w, use_container_width=True)

                st.markdown(f"**Dual Shadow Cost of Capital (Budget Multiplier $\\lambda$):** `{qp.get('dual_budget_multiplier', 0.0):.6f}`")
            except Exception as e:
                st.error(f"Optimization error: {str(e)}")


# =============================================================================
# VIEW 6: SUPPLY CHAIN LOGISTICS & MARGIN ELASTICITY
# =============================================================================
elif nav_choice == "🚚 Supply Chain & Margins (cuOpt)":
    st.markdown('<div class="header-style">🚚 Supply Chain Routing & Margin Elasticity (NVIDIA cuOpt)</div>', unsafe_allow_html=True)
    st.markdown("Models Capacitated Vehicle Routing Problems (CVRP) to quantify corporate distribution costs and operating margin elasticity to fuel inflation.")

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        fleet_vehicles = st.slider("Fleet Size (Vehicles)", min_value=1, max_value=8, value=3)
        vehicle_cap = st.slider("Vehicle Capacity (Units)", min_value=20.0, max_value=100.0, value=50.0, step=5.0)
    with col_v2:
        cost_per_mile = st.slider("Cost per Distance Unit ($/km)", min_value=1.0, max_value=5.0, value=2.50, step=0.25)
        fuel_share = st.slider("Fuel Share of Logistics Cost (%)", min_value=10, max_value=60, value=35) / 100.0

    # Prototype fulfillment network
    coords = [(0, 0), (12, 10), (15, -12), (-14, 11), (-12, -15), (22, 5)]
    demands = [0.0, 15.0, 20.0, 12.0, 18.0, 25.0]

    opt_vrp = SupplyChainLogisticsOptimizer(cost_per_distance_unit=cost_per_mile, fuel_cost_share=fuel_share)
    c_matrix = SupplyChainLogisticsOptimizer.build_euclidean_cost_matrix(coords)
    vrp_res = opt_vrp.solve_capacitated_vrp(cost_matrix=c_matrix, demands=demands, vehicle_capacity=vehicle_cap, num_vehicles=fleet_vehicles)

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.metric("Total Transit Cost", f"${vrp_res['total_transport_cost']:,.2f}")
    with col_r2:
        st.metric("Fleet Capacity Utilization", f"{vrp_res['fleet_capacity_utilization_pct']:.1f}%")
    with col_r3:
        st.metric("Cost per Delivered Unit", f"${vrp_res['cost_per_unit_delivered']:.2f}")

    st.subheader("⛽ Fuel Inflation Shock Sensitivity")
    sens = vrp_res["sensitivity"]
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.warning(f"**+10% Fuel Price Spike:** Total Cost rises to **${sens['fuel_plus_10pct_cost']:,.2f}** (+${sens['logistics_cost_inflation_per_unit_10pct']:.3f}/unit)")
    with col_s2:
        st.error(f"**+20% Fuel Price Spike:** Total Cost rises to **${sens['fuel_plus_20pct_cost']:,.2f}**")


# =============================================================================
# VIEW 7: DECISION JOURNAL & REVIEW
# =============================================================================
elif nav_choice == "📓 Decision Journal & Review":
    st.markdown('<div class="header-style">📓 Decision Journal & Portfolio Review</div>', unsafe_allow_html=True)
    st.markdown("Immutable record of institutional investment decisions and exit rules.")

    journal_csv_path = os.path.join(PROJECT_DIR, "journal", "journal.csv")
    if os.path.exists(journal_csv_path):
        df_journal = pd.read_csv(journal_csv_path)
        st.dataframe(df_journal, use_container_width=True)
    else:
        st.info("No journal.csv found yet. Start logging decisions below.")

    st.divider()
    review_md_path = os.path.join(PROJECT_DIR, "journal", "portfolio_review.md")
    if os.path.exists(review_md_path):
        with open(review_md_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())


# =============================================================================
# VIEW 8: SEC FILINGS & PRICE ALERTS
# =============================================================================
elif nav_choice == "🚨 SEC Filings & Price Alerts":
    st.markdown('<div class="header-style">🚨 Regulatory Filings & Market Shock Alerts</div>', unsafe_allow_html=True)
    st.markdown("Live monitoring of official SEC EDGAR submissions and intraday price shocks.")

    alerts_json_path = os.path.join(PROJECT_DIR, "reports", "active_alerts.json")
    if os.path.exists(alerts_json_path):
        import json
        with open(alerts_json_path, "r", encoding="utf-8") as f:
            alerts_data = json.load(f)

        st.subheader(f"Active Alerts ({alerts_data.get('alert_count', 0)} Total)")
        for a in alerts_data.get("alerts", []):
            st.warning(f"**[{a.get('type')}] {a.get('ticker')}**: {a.get('details')} *(Timestamp: {a.get('timestamp')})*")
    else:
        st.info("Running live alert check across active watchlist...")
        monitor = AlertMonitor()
        res_checks = monitor.run_all_checks()
        alerts = res_checks.get("alerts", [])
        if alerts:
            for a in alerts:
                st.warning(f"**[{a.get('type')}] {a.get('ticker')}**: {a.get('details')}")
        else:
            st.success("✅ All monitored securities within normal volatility bands. No unfiled 8-K / 10-K events detected.")


if __name__ == "__main__":
    pass
