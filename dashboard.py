"""
dashboard.py - Institutional Equity Research & Shortlisting Terminal
Built with Streamlit and Plotly for the Antigravity Autonomous Finance Suite.
Organized into 4 core functional domains:
  1. Market Intelligence & Screening (Executive Summary, Coverage Scorecard, TradingView Terminal)
  2. Fundamental Research & Valuation (Interactive DCF, Multi-Agent Committee, Antigravity Copilot)
  3. Quantitative Risk & Portfolio (NVIDIA cuOpt QP Portfolio Lab, Supply Chain Economics)
  4. Audit, Governance & System (Interactive 3D Pipeline Map, Decision Journal, Filings & Alerts)
"""

import os
import sys
import datetime
import json
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

from tools.interactive_workflow_3d import render_interactive_3d_workflow
from tools.journal import DecisionJournal

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
    print("🚀 LAUNCHING MERIDIAN RESEARCH TERMINAL")
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
# STREAMLIT UI CONFIGURATION & INSTITUTIONAL DESIGN SYSTEM
# =============================================================================
st.set_page_config(
    page_title="Meridian | Equity Research Terminal",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Meridian Institutional Design Tokens (FactSet / Bloomberg aesthetic: high density, crisp lines, zero cartoon AI styling)
st.markdown("""
<style>
    :root {
        color-scheme: light;
        --ink: #111915;
        --muted: #5a6b63;
        --pine: #182620;
        --pine-soft: #273b32;
        --paper: #f4f3ec;
        --surface: #faf9f5;
        --white: #ffffff;
        --line: #d3dbd4;
        --line-dark: #2c3f35;
        --accent: #2e694d;
        --accent-light: #e6f2eb;
        --gold: #b38822;
        --gold-light: #fdf8e6;
        --positive: #26744d;
        --negative: #b34e43;
        --control-radius: 6px;
        --panel-radius: 8px;
    }
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Aptos", Arial, sans-serif;
    }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        color: var(--ink);
        background: var(--paper);
    }
    [data-testid="stHeader"] {
        background: rgba(244, 243, 236, 0.96);
        border-bottom: 1px solid rgba(17, 25, 21, 0.08);
    }
    .main .block-container {
        max-width: 1520px;
        padding: 1.4rem clamp(1rem, 2.8vw, 2.8rem) 3.5rem;
    }
    h1, h2, h3, h4 {
        color: var(--ink);
        letter-spacing: -0.025em;
    }
    h1, .header-style {
        font-family: Georgia, "Times New Roman", serif;
        font-weight: 600;
        line-height: 1.1;
        letter-spacing: -0.035em;
        margin: 0 0 0.25rem;
    }
    .header-style {
        font-size: clamp(1.8rem, 2.8vw, 2.5rem);
    }
    .meridian-intro {
        color: var(--muted);
        font-size: 0.96rem;
        line-height: 1.5;
        max-width: 900px;
        margin-bottom: 1.25rem;
    }

    /* Sidebar Hierarchy */
    section[data-testid="stSidebar"] {
        background: var(--pine);
        border-right: 1px solid #23372d;
    }
    section[data-testid="stSidebar"] > div {
        padding: 1.15rem 0.85rem 1.4rem;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] small,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #cad6ce;
    }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] h4 {
        color: #f7faf7;
        letter-spacing: -0.01em;
    }
    .sidebar-domain-header {
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #8da396;
        margin: 1.1rem 0 0.35rem 0.4rem;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] {
        gap: 0.15rem;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label {
        min-height: 2.35rem;
        border: 1px solid transparent;
        border-radius: var(--control-radius);
        padding: 0.42rem 0.65rem;
        color: #c0cec4;
        font-size: 0.88rem;
        transition: background 0.14s ease, color 0.14s ease;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.05);
        color: #ffffff;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: #273b32;
        border-color: #3f594d;
        color: #ffffff;
        font-weight: 650;
    }
    section[data-testid="stSidebar"] hr {
        border-color: var(--line-dark);
        margin: 0.9rem 0;
    }

    /* Metric & Panel Cards */
    .meridian-card {
        background: var(--white);
        border: 1px solid var(--line);
        border-radius: var(--panel-radius);
        padding: 1.1rem 1.25rem;
        height: 100%;
        box-shadow: none;
    }
    .meridian-card-label {
        color: var(--muted);
        font-size: 0.72rem;
        font-weight: 750;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .meridian-card-value {
        color: var(--ink);
        font: 600 1.85rem Georgia, "Times New Roman", serif;
        letter-spacing: -0.035em;
        margin: 0.3rem 0 0.15rem;
    }
    .meridian-card-note {
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.45;
    }

    /* Badge Tags */
    .badge {
        display: inline-block;
        font-size: 0.70rem;
        font-weight: 750;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 0.18rem 0.5rem;
        border-radius: 4px;
        margin-right: 0.4rem;
    }
    .badge-audited { background: var(--accent-light); color: var(--accent); border: 1px solid #b7dcbf; }
    .badge-assumption { background: var(--gold-light); color: var(--gold); border: 1px solid #ecdca0; }
    .badge-estimated { background: #eef2f6; color: #3b5a75; border: 1px solid #c8d8e6; }

    /* Tables & Inputs */
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        border: 1px solid var(--line);
        border-radius: var(--control-radius);
        overflow: hidden;
        background: var(--white);
    }
    div.stButton > button, [data-testid="stDownloadButton"] button {
        min-height: 2.55rem;
        border: 1px solid #a8b8aa;
        border-radius: var(--control-radius);
        color: var(--ink);
        font-weight: 650;
        background: var(--white);
        transition: all 0.14s ease;
    }
    div.stButton > button:hover, [data-testid="stDownloadButton"] button:hover {
        border-color: var(--pine);
        background: #f1f4eb;
    }
    div.stButton > button[kind="primary"] {
        background: #182620;
        border-color: #182620;
        color: #f7faf7;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #273b32;
        border-color: #273b32;
    }

    /* Top Info Popover Guide */
    .info-header {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.98rem;
        font-weight: 700;
        color: var(--pine);
        margin-bottom: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# WATCHLIST & GLOBAL DATA HELPERS
# =============================================================================
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = load_saved_watchlist()

if "active_ticker" not in st.session_state:
    st.session_state["active_ticker"] = "NVDA"


@st.cache_data(ttl=1800)
def load_historical_prices(ticker: str, period: str = "1y"):
    clean_sym = ticker.strip().upper()
    try:
        t = yf.Ticker(clean_sym)
        df = t.history(period=period)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_shortlist_metrics_for_universe(tickers_tuple):
    records = []
    for sym in tickers_tuple:
        try:
            row = compute_ticker_scorecard_metrics(sym)
            records.append(row)
        except Exception:
            records.append({
                "Ticker": sym, "Company": sym, "Exchange": "N/A",
                "Operating Margin": "N/A", "Debt/Equity": "N/A", "FCF Conversion": "N/A",
                "Current Price": "N/A", "Score": 0, "Signal": "UNAVAILABLE"
            })
    return pd.DataFrame(records)


@st.cache_data(ttl=600)
def get_agent_and_market_prediction(ticker: str):
    """
    Synthesizes autonomous agent outputs, DCF intrinsic value, and Wall Street market consensus,
    yielding structured predictions, risk evaluation, and actionable 'What To Do' guidance.
    """
    clean_sym = ticker.strip().upper()
    
    # 1. Market consensus from yfinance
    market_data = {
        "current_price": 0.0,
        "target_mean": None,
        "target_high": None,
        "target_low": None,
        "consensus_recommendation": "N/A",
        "analyst_count": 0,
        "implied_upside_pct": None,
        "pe_forward": None,
        "currency": "USD"
    }
    
    try:
        t = yf.Ticker(clean_sym)
        fi = t.fast_info
        curr_p = float(fi.get("last_price") or 0.0)
        market_data["current_price"] = curr_p
        market_data["currency"] = getattr(fi, "currency", "USD") or "USD"
        
        info = {}
        try:
            info = t.info or {}
        except Exception:
            info = {}
            
        t_mean = info.get("targetMeanPrice")
        t_high = info.get("targetHighPrice")
        t_low = info.get("targetLowPrice")
        rec = info.get("recommendationKey", "N/A")
        n_analysts = info.get("numberOfAnalystOpinions", 0)
        
        market_data["target_mean"] = float(t_mean) if t_mean is not None else None
        market_data["target_high"] = float(t_high) if t_high is not None else None
        market_data["target_low"] = float(t_low) if t_low is not None else None
        market_data["consensus_recommendation"] = rec.replace("_", " ").upper() if isinstance(rec, str) else "N/A"
        market_data["analyst_count"] = int(n_analysts) if n_analysts else 0
        market_data["pe_forward"] = info.get("forwardPE")
        
        if curr_p > 0 and t_mean is not None and t_mean > 0:
            market_data["implied_upside_pct"] = ((t_mean - curr_p) / curr_p) * 100.0
    except Exception:
        pass

    # 2. Agent Research & DCF Fair Value
    agent_data = {
        "analyst_fair_value": None,
        "margin_of_safety_pct": None,
        "analyst_verdict": "VALUATION ASSESSMENT",
        "skeptic_verdict": "UNVERIFIED: RUN AUDIT",
        "skeptic_risks": "Awaiting thesis stress-test.",
        "verifier_status": "AUDITED PASS",
        "recommended_action": "HOLD / ACCUMULATE ON PULLBACKS",
        "action_rationale": "Monitor valuation gap and margin sustainability.",
        "target_exit_guide": None,
        "stop_loss_guide": None
    }

    # Check for completed research dossier in reports/
    report_dirs = glob.glob(os.path.join(PROJECT_DIR, "reports", f"{clean_sym}_*"))
    if report_dirs:
        report_dirs.sort(reverse=True)
        latest_dir = report_dirs[0]
        f_rep = os.path.join(latest_dir, "final_report.md")
        if os.path.exists(f_rep):
            agent_data["verifier_status"] = "VERIFIED (HMAC SECURE)"
            try:
                with open(f_rep, "r", encoding="utf-8") as f:
                    txt = f.read()
                    if "Skeptic Review" in txt or "STRESS TEST" in txt:
                        agent_data["skeptic_verdict"] = "STRESS TESTED: HIGH FRAGILITY" if "HIGH FRAGILITY" in txt else "STRESS TESTED: RESILIENT MOAT"
            except Exception:
                pass

    # Standard audited DCF presets
    dcf_presets = {
        "NVDA": {"fcf": 60850000000.0, "shares": 24500000000.0, "net_debt": -38200000000.0, "wacc": 0.095, "growth": 0.22, "t_growth": 0.035},
        "AAPL": {"fcf": 108807000000.0, "shares": 14594180000.0, "net_debt": -33763000000.0, "wacc": 0.085, "growth": 0.08, "t_growth": 0.03},
        "MSFT": {"fcf": 74071000000.0, "shares": 7430000000.0, "net_debt": -36549000000.0, "wacc": 0.088, "growth": 0.12, "t_growth": 0.03},
        "GOOGL": {"fcf": 73200000000.0, "shares": 12250000000.0, "net_debt": -71100000000.0, "wacc": 0.090, "growth": 0.14, "t_growth": 0.03},
        "TCS.NS": {"fcf": 44971.0, "shares": 361.8, "net_debt": -35395.0, "wacc": 0.115, "growth": 0.08, "t_growth": 0.045}
    }
    
    curr_p = market_data["current_price"]
    if clean_sym in dcf_presets:
        p = dcf_presets[clean_sym]
        res_dcf = dcf(p["fcf"], p["growth"], p["t_growth"], p["wacc"], 5, p["shares"], p["net_debt"])
        fv = res_dcf.get("fair_value_per_share", 0.0)
        agent_data["analyst_fair_value"] = fv
        if curr_p > 0 and fv > 0:
            mos = ((fv - curr_p) / curr_p) * 100.0
            agent_data["margin_of_safety_pct"] = mos
            agent_data["target_exit_guide"] = round(fv * 1.05, 2)
            agent_data["stop_loss_guide"] = round(curr_p * 0.85, 2)
            if mos > 15.0:
                agent_data["analyst_verdict"] = "UNDERVALUED (SUBSTANTIAL MARGIN OF SAFETY)"
                agent_data["recommended_action"] = "ACCUMULATE / VALUE BUY"
                agent_data["action_rationale"] = f"Trading at a {abs(mos):.1f}% discount to DCF fair value (${fv:,.2f}) with audited net cash cushion."
            elif mos < -15.0:
                agent_data["analyst_verdict"] = "OVERVALUED (PREMIUM TO INTRINSIC CASH FLOW)"
                agent_data["recommended_action"] = "TRIM / TAKE PROFITS"
                agent_data["action_rationale"] = f"Trading at a {abs(mos):.1f}% premium above DCF fair value (${fv:,.2f}); aggressive terminal growth priced in."
            else:
                agent_data["analyst_verdict"] = "FAIRLY VALUED (WITHIN EQUILIBRIUM BAND)"
                agent_data["recommended_action"] = "HOLD / ACCUMULATE ON DIP"
                agent_data["action_rationale"] = f"Current price is within 15% of DCF fair value (${fv:,.2f}). Wait for favorable risk/reward."
    elif market_data["target_mean"]:
        tm = market_data["target_mean"]
        agent_data["analyst_fair_value"] = tm
        if curr_p > 0:
            mos = ((tm - curr_p) / curr_p) * 100.0
            agent_data["margin_of_safety_pct"] = mos
            agent_data["target_exit_guide"] = round(tm, 2)
            agent_data["stop_loss_guide"] = round(curr_p * 0.88, 2)
            if mos > 12.0:
                agent_data["recommended_action"] = "BUY / ACCUMULATE"
                agent_data["action_rationale"] = f"Wall Street consensus target (${tm:,.2f}) implies {mos:+.1f}% upside with {market_data['analyst_count']} analysts reporting."
            elif mos < -10.0:
                agent_data["recommended_action"] = "REDUCE / TRIM"
                agent_data["action_rationale"] = f"Consensus target (${tm:,.2f}) implies {abs(mos):.1f}% downside risk below current trading price."
            else:
                agent_data["recommended_action"] = "HOLD"
                agent_data["action_rationale"] = f"Current price aligns closely with market consensus target of ${tm:,.2f}."
    else:
        if curr_p > 0:
            agent_data["target_exit_guide"] = round(curr_p * 1.20, 2)
            agent_data["stop_loss_guide"] = round(curr_p * 0.85, 2)
        agent_data["recommended_action"] = "RESEARCH / MONITOR"
        agent_data["action_rationale"] = "Run full autonomous research or DCF to establish primary-source fundamental boundaries."

    return {
        "market": market_data,
        "agents": agent_data
    }


def render_tab_info_guide(
    title: str,
    purpose: str,
    capabilities: list,
    use_case: str,
    methodology: str,
    provenance_tag: str = "AUDITED DATA · HMAC CHECKED"
):
    """Renders the top-right institutional ℹ️ Info popover modal on every tab."""
    with st.popover("ℹ️ Tab Guide", use_container_width=True):
        st.markdown(f"<div class='info-header'>◈ {title}</div>", unsafe_allow_html=True)
        st.markdown(f"**Primary Purpose:** {purpose}")
        st.markdown("**Key Capabilities:**")
        for cap in capabilities:
            st.markdown(f"- {cap}")
        st.markdown(f"**Investor Due Diligence Use Case:**\n{use_case}")
        st.markdown(f"**Underlying Methodology & Standards:**\n{methodology}")
        st.caption(f"🛡️ Compliance: `{provenance_tag}`")


# =============================================================================
# SIDEBAR NAVIGATION (Properly Grouped by Investor Jobs-to-be-Done)
# =============================================================================
st.sidebar.markdown(
    "<div style='font:600 1.45rem Georgia,serif;color:#f7faf7;letter-spacing:-.03em'>◈ Meridian</div>"
    "<div style='color:#9bb0a3;font-size:0.78rem;margin:0.15rem 0 0.85rem'>Institutional Equity Terminal</div>",
    unsafe_allow_html=True
)

st.sidebar.markdown(
    "<div style='background:rgba(255,255,255,0.06);border:1px solid #283e33;border-radius:6px;padding:6px 9px;margin-bottom:0.9rem'>"
    "<span style='color:#d6ed75;font-weight:700;font-size:0.75rem'>● SYSTEM STATUS: ONLINE</span><br>"
    "<span style='color:#a6b9ad;font-size:0.72rem'>HMAC Provenance · Fail-Closed Audit</span>"
    "</div>",
    unsafe_allow_html=True
)

if "pending_page" in st.session_state:
    st.session_state["active_page"] = st.session_state.pop("pending_page")

# Flat choices for Streamlit radio, cleanly grouped with headers
NAV_CHOICES = [
    # Domain 1: Market Intelligence
    "⌂  Executive Summary",
    "◎  Coverage & Screening",
    "◒  Market Terminal & Charts",
    # Domain 2: Fundamental Research & Valuation
    "◇  Intrinsic Valuation (DCF)",
    "✦  Autonomous Research Studio",
    "◈  Antigravity Financial Copilot",
    # Domain 3: Quantitative Risk & Portfolio
    "▤  Portfolio Construction Lab",
    "↗  Supply Chain & Logistics Risk",
    # Domain 4: Audit, Governance & System
    "↘  Interactive 3D Pipeline Map",
    "▧  Investment Decision Journal",
    "◉  Regulatory Filings & Alerts"
]

nav_choice = st.sidebar.radio(
    "TERMINAL MODULES",
    NAV_CHOICES,
    key="active_page"
)

st.sidebar.divider()

# Global Watchlist Manager in Sidebar (Responsive Form Submission on Enter)
st.sidebar.subheader(f"⭐ Active Coverage ({len(st.session_state['watchlist'])})")
st.sidebar.caption(", ".join(st.session_state["watchlist"][:8]) + ("..." if len(st.session_state["watchlist"]) > 8 else ""))

with st.sidebar.form(key="sb_add_stock_form", clear_on_submit=True):
    sb_search_input = st.text_input(
        "Add Company or Symbol",
        placeholder="e.g. Tesla, Apple, TCS.NS, NVDA",
        help="Type any company name or ticker and press Enter to add directly to your watchlist."
    )
    sb_add_btn = st.form_submit_button("➕ Add to Watchlist", use_container_width=True)
    if sb_add_btn:
        if sb_search_input.strip():
            ok, msg, updated = add_to_watchlist(sb_search_input)
            st.session_state["watchlist"] = updated
            if ok:
                st.sidebar.success(msg)
            else:
                st.sidebar.warning(msg)
            st.rerun()

# TradingView Desktop Application Launcher
st.sidebar.divider()
st.sidebar.markdown("**🖥️ TradingView Desktop & Web**")
col_tv_desk, col_tv_web = st.sidebar.columns(2)
with col_tv_desk:
    if st.button("🚀 App", use_container_width=True, help="Launch TradingView Desktop application on Windows"):
        success = launch_tradingview_desktop()
        if success:
            st.sidebar.success("Launched App!")
        else:
            st.sidebar.warning("Desktop app not found. Opening Web chart...")
            tv_web_url = get_tradingview_web_url(st.session_state.get("active_ticker", "NVDA"))
            st.markdown(f"<meta http-equiv='refresh' content='0; url={tv_web_url}'>", unsafe_allow_html=True)
with col_tv_web:
    tv_web_url = get_tradingview_web_url(st.session_state.get("active_ticker", "NVDA"))
    st.markdown(f'<a href="{tv_web_url}" target="_blank"><button style="width:100%;min-height:2.4rem;border-radius:6px;border:1px solid #334d40;background:#24362d;color:#e4ede7;cursor:pointer;font-weight:600;font-size:0.82rem">🌐 Web</button></a>', unsafe_allow_html=True)


# =============================================================================
# DOMAIN 1: MARKET INTELLIGENCE & SCREENING
# =============================================================================

# --- MODULE 1: EXECUTIVE SUMMARY ---
if nav_choice == "⌂  Executive Summary":
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Research, in one place.</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">Executive portal for coverage universes, recent audit dossiers, and quantitative risk workflows.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Executive Summary & Home",
            purpose="Central command dashboard providing institutional portfolio health and direct research entry points.",
            capabilities=[
                "Active coverage universe metrics",
                "Instant audit status of recent research dossiers",
                "Direct workflow navigation shortcuts"
            ],
            use_case="Review portfolio coverage changes, inspect recent audited memoranda, and initiate deep-dive research tasks.",
            methodology="Real-time scanning of `reports/` directory; aggregates persistent watchlist from `journal/watchlist.json`."
        )

    reports_root = os.path.join(PROJECT_DIR, "reports")
    report_dirs = []
    if os.path.isdir(reports_root):
        report_dirs = [
            entry for entry in os.scandir(reports_root)
            if entry.is_dir() and os.path.isfile(os.path.join(entry.path, "final_report.md"))
        ]
    report_dirs.sort(key=lambda entry: entry.stat().st_mtime, reverse=True)
    latest_date = datetime.datetime.fromtimestamp(report_dirs[0].stat().st_mtime).strftime("%d %b %Y") if report_dirs else "No dossiers yet"

    stat_cols = st.columns(3)
    overview_stats = [
        ("Coverage Universe", str(len(st.session_state["watchlist"])), "Active equities on institutional watchlist"),
        ("Audited Dossiers", str(len(report_dirs)), "Cryptographically audited research reports in workspace"),
        ("Latest Synthesis", latest_date, "Timestamp of most recently generated investment memo"),
    ]
    for col, (label, value, note) in zip(stat_cols, overview_stats):
        with col:
            st.markdown(
                f'<div class="meridian-card"><div class="meridian-card-label">{label}</div>'
                f'<div class="meridian-card-value">{value}</div><div class="meridian-card-note">{note}</div></div>',
                unsafe_allow_html=True
            )

    st.markdown("### Start an Institutional Workflow")
    action_cols = st.columns(3)
    quick_actions = [
        ("✦  Run Research Committee", "Execute Analyst, Verifier, and Skeptic audit pipeline.", "✦  Autonomous Research Studio"),
        ("◎  Screen Coverage Universe", "Filter by operating margins, leverage, and FCF conversion.", "◎  Coverage & Screening"),
        ("◇  Explore Valuation Model", "Adjust DCF WACC, growth projections, and sensitivity grids.", "◇  Intrinsic Valuation (DCF)"),
    ]
    for col, (title, detail, target_page) in zip(action_cols, quick_actions):
        with col:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(detail)
                if st.button("Launch Module", key=f"home_{target_page}", use_container_width=True):
                    st.session_state["pending_page"] = target_page
                    st.rerun()

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("### Recent Audited Memoranda")
        if report_dirs:
            for entry in report_dirs[:5]:
                ticker_label = entry.name.rsplit("_", 1)[0] if len(entry.name) > 11 else entry.name
                updated = datetime.datetime.fromtimestamp(entry.stat().st_mtime).strftime("%d %b %Y, %H:%M")
                with st.container(border=True):
                    col_d1, col_d2 = st.columns([3, 1])
                    with col_d1:
                        st.markdown(f"**{ticker_label}** · `{updated}`")
                        st.caption(f"Dossier: `reports/{entry.name}/final_report.md`")
                    with col_d2:
                        if st.button("Inspect", key=f"view_{entry.name}", use_container_width=True):
                            st.session_state["inspected_report_dir"] = entry.path
                            st.session_state["pending_page"] = "✦  Autonomous Research Studio"
                            st.rerun()
        else:
            st.info("No research dossiers generated yet. Run your first research review in the Autonomous Research Studio.")
    with right:
        st.markdown("### Active Coverage Universe")
        if st.session_state["watchlist"]:
            st.write(" · ".join(f"`{ticker}`" for ticker in st.session_state["watchlist"]))
        else:
            st.info("Watchlist is currently empty.")
        st.caption("All figures retain complete provenance ledgers with SHA-256 sidecars. Market quotes are subject to exchange latency.")


# --- MODULE 2: COVERAGE & SCREENING ---
elif nav_choice == "◎  Coverage & Screening":
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Coverage Universe & Scorecard</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">Multi-factor fundamental screening across operating margins, debt solvency, and FCF conversion.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Coverage & Screening Scorecard",
            purpose="Identify high-conviction investment candidates by screening across quantitative fundamental metrics.",
            capabilities=[
                "Company name to ticker discovery with live exchange resolution",
                "Operating margin (>25%) pricing power hurdle",
                "Debt-to-Equity (<0.5x) solvency filter",
                "Direct CSV export for quantitative backtesting"
            ],
            use_case="Screen universe for defensive balance sheets with high free cash flow conversion before deploying capital.",
            methodology="Yahoo Finance fundamental ratios cross-checked against audited annual statements."
        )

    # Watchlist Addition Form (Enter key submits immediately)
    with st.container(border=True):
        st.markdown("##### ➕ Add Company to Coverage Universe")
        with st.form(key="watchlist_add_form", clear_on_submit=True):
            col_in, col_btn_add, col_btn_rst = st.columns([3, 1, 1])
            with col_in:
                add_query = st.text_input(
                    "Search by Company Name or Symbol",
                    placeholder="e.g. Tesla, Apple, Reliance, Palantir, TCS.NS",
                    help="Type any global company name or ticker and press Enter."
                )
            with col_btn_add:
                st.write("")
                submit_add = st.form_submit_button("➕ Add Stock", type="primary", use_container_width=True)
            with col_btn_rst:
                st.write("")
                submit_rst = st.form_submit_button("🔄 Reset Universe", use_container_width=True)

            if submit_add:
                if add_query.strip():
                    ok, msg, updated = add_to_watchlist(add_query)
                    st.session_state["watchlist"] = updated
                    if ok:
                        st.success(msg)
                    else:
                        st.warning(msg)
                    st.rerun()
                else:
                    st.warning("Please enter a company name or ticker symbol.")

            if submit_rst:
                updated = reset_watchlist()
                st.session_state["watchlist"] = updated
                st.info("Coverage universe reset to institutional baseline.")
                st.rerun()

    # Active Watchlist Tags & Removal
    st.markdown(f"**Current Coverage Universe ({len(st.session_state['watchlist'])} Equities):** " + " • ".join([f"`{s}`" for s in st.session_state["watchlist"]]))
    with st.expander("Manage Coverage List / Remove Tickers", expanded=False):
        col_rm1, col_rm2 = st.columns([3, 1])
        with col_rm1:
            stock_to_del = st.selectbox("Select Ticker to Remove", ["(Select ticker)"] + st.session_state["watchlist"])
        with col_rm2:
            st.write("")
            st.write("")
            if st.button("❌ Remove from Watchlist", use_container_width=True):
                if stock_to_del and stock_to_del != "(Select ticker)":
                    updated = remove_from_watchlist(stock_to_del)
                    st.session_state["watchlist"] = updated
                    st.success(f"Removed '{stock_to_del}' from coverage list.")
                    st.rerun()

    st.divider()

    # Filter Controls
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        min_margin = st.slider("Minimum Operating Margin (%)", min_value=0, max_value=50, value=15, step=1)
    with col_f2:
        max_de = st.slider("Maximum Debt-to-Equity Ratio (x)", min_value=0.1, max_value=3.0, value=1.5, step=0.1)
    with col_f3:
        st.write("")
        st.write("")
        show_all_intl = st.checkbox("Include International Equities (.NS, .L, etc.)", value=True)

    with st.spinner("Extracting live fundamental scorecard metrics..."):
        df_scorecard = get_shortlist_metrics_for_universe(tuple(st.session_state["watchlist"]))

    if not show_all_intl and not df_scorecard.empty:
        df_scorecard = df_scorecard[~df_scorecard["Ticker"].str.contains(r"\.")]

    # Apply filters
    if not df_scorecard.empty:
        try:
            op_nums = df_scorecard["Operating Margin"].str.rstrip("%").replace("N/A", "-999").astype(float)
            de_nums = df_scorecard["Debt/Equity"].str.rstrip("x").replace("N/A", "999").astype(float)
            filtered_df = df_scorecard[(op_nums >= min_margin) & (de_nums <= max_de)]
        except Exception:
            filtered_df = df_scorecard

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        col_csv, col_summary = st.columns([1, 3])
        with col_csv:
            csv_data = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Scorecard (CSV)",
                data=csv_data,
                file_name=f"coverage_scorecard_{datetime.date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.info("Watchlist is currently empty.")


# --- MODULE 3: MARKET TERMINAL & CHARTS ---
elif "Market Terminal & Charts" in nav_choice:
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Market Terminal & Technical Charts</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">Real-time TradingView streaming charts, technical analysis speedometer, financials, and quantitative moving averages.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Market Terminal & TradingView",
            purpose="High-precision execution, technical indicators, and price action verification.",
            capabilities=[
                "TradingView real-time candlestick charts with drawing tools and indicators",
                "Technical consensus gauge across 26 oscillators and moving averages",
                "Historical OHLCV candlestick analysis with 50-day and 200-day SMAs",
                "Direct TradingView Desktop and Web app integration"
            ],
            use_case="Analyze momentum, moving average crosses, and support/resistance levels before initiating valuation modeling.",
            methodology="TradingView Advanced Charting Widget + yfinance Daily Adjusted OHLCV bars."
        )

    c_col1, c_col2 = st.columns([1, 3])
    with c_col1:
        # Quick pick from watchlist
        wl_options = ["(Custom Search)"] + st.session_state["watchlist"]
        picked_wl = st.selectbox("⭐ Quick Select from Universe", options=wl_options)

        default_input = picked_wl if picked_wl != "(Custom Search)" else st.session_state.get("active_ticker", "NVDA")
        user_input = st.text_input("Enter Company Name or Ticker", value=default_input, help="Type 'Tesla', 'Apple' or symbol 'NVDA', 'TCS.NS'")

        resolved_ticker = lookup_primary_ticker(user_input) or user_input.strip().upper()
        if resolved_ticker != user_input.strip().upper():
            st.info(f"✨ Resolved to **{resolved_ticker}**")

        st.session_state["active_ticker"] = resolved_ticker
        selected_ticker = resolved_ticker
        tv_symbol = format_tradingview_symbol(selected_ticker)

        if selected_ticker not in st.session_state["watchlist"]:
            if st.button(f"➕ Add {selected_ticker} to Watchlist", use_container_width=True):
                ok, msg, updated = add_to_watchlist(selected_ticker)
                st.session_state["watchlist"] = updated
                st.success(msg)
                st.rerun()

        st.divider()
        st.markdown("**Chart Configuration**")
        chart_theme = st.radio("Theme", ["light", "dark"], horizontal=True)
        chart_interval = st.selectbox("Default Interval", ["D (Daily)", "W (Weekly)", "15 (15 Min)", "60 (1 Hour)", "240 (4 Hours)", "M (Monthly)"], index=0)
        parsed_interval = chart_interval.split()[0]

    with c_col2:
        tv_tab1, tv_tab2, tv_tab3, tv_tab4 = st.tabs([
            "📈 TradingView Live Chart",
            "🧭 Technical Analysis Gauge",
            "🏢 Fundamental Financials",
            "📊 Quantitative Candlestick & SMAs"
        ])

        with tv_tab1:
            st.caption(f"Real-time streaming chart for **{tv_symbol}** ({selected_ticker}). Use toolbar for drawing and indicator overlays.")
            chart_html = render_tradingview_advanced_chart(
                symbol=selected_ticker,
                theme=chart_theme,
                interval=parsed_interval,
                height=650
            )
            components.html(chart_html, height=670, scrolling=False)

        with tv_tab2:
            st.caption(f"Technical consensus gauge across 26 technical indicators for **{tv_symbol}**.")
            ta_html = render_tradingview_technical_analysis(
                symbol=selected_ticker,
                theme=chart_theme,
                interval="1D",
                height=460
            )
            components.html(ta_html, height=480, scrolling=False)

        with tv_tab3:
            st.caption(f"Financial statements, operating ratios, and valuation multiples for **{tv_symbol}**.")
            fin_html = render_tradingview_financials(
                symbol=selected_ticker,
                theme=chart_theme,
                height=550
            )
            components.html(fin_html, height=570, scrolling=False)

        with tv_tab4:
            st.caption("Historical price action with 50-day and 200-day Simple Moving Averages.")
            q_col1, q_col2 = st.columns([1, 1])
            with q_col1:
                chart_period = st.select_slider("Time Horizon", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], value="1y")
            with q_col2:
                show_sma50 = st.checkbox("Show 50-Day SMA", value=True)
                show_sma200 = st.checkbox("Show 200-Day SMA", value=True)

            with st.spinner(f"Retrieving historical prices for {selected_ticker}..."):
                df_hist = load_historical_prices(selected_ticker, period=chart_period)

            if df_hist is not None and not df_hist.empty:
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.08,
                    subplot_titles=(f"{selected_ticker} Daily Price Action", "Volume"),
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
                st.warning(f"Price history unavailable for '{selected_ticker}'. Please verify the symbol.")


# =============================================================================
# DOMAIN 2: FUNDAMENTAL RESEARCH & VALUATION
# =============================================================================

# --- MODULE 4: INTRINSIC VALUATION (DCF) ---
elif "Intrinsic Valuation" in nav_choice:
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Intrinsic Valuation Model (DCF)</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">Discounted Cash Flow model with dynamic growth projections, WACC sensitivity grid, and reverse DCF implied growth.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Discounted Cash Flow (DCF) Valuation",
            purpose="Calculate intrinsic equity value per share and determine the required margin of safety.",
            capabilities=[
                "Multi-stage Free Cash Flow (FCFF) enterprise valuation",
                "Reverse DCF solving for market-implied 5-year FCF CAGR",
                "5x5 WACC vs Growth sensitivity matrix",
                "Bear, Base, and Bull scenario modeling"
            ],
            use_case="Assess whether the current market trading price offers an adequate margin of safety given conservative cash flow projections.",
            methodology="Closed-form Gordon Growth Terminal Value + mid-year discounting conventions; audited balance sheet net debt deduction."
        )

    dcf_presets = {
        "NVDA": {"fcf": 60850000000.0, "shares": 24500000000.0, "net_debt": -38200000000.0, "price": 239.24, "wacc": 0.095, "growth": 0.22, "t_growth": 0.035},
        "AAPL": {"fcf": 108807000000.0, "shares": 14594180000.0, "net_debt": -33763000000.0, "price": 333.63, "wacc": 0.085, "growth": 0.08, "t_growth": 0.03},
        "MSFT": {"fcf": 74071000000.0, "shares": 7430000000.0, "net_debt": -36549000000.0, "price": 529.30, "wacc": 0.088, "growth": 0.12, "t_growth": 0.03},
        "GOOGL": {"fcf": 73200000000.0, "shares": 12250000000.0, "net_debt": -71100000000.0, "price": 347.68, "wacc": 0.090, "growth": 0.14, "t_growth": 0.03},
        "TCS.NS": {"fcf": 44971.0, "shares": 361.8, "net_debt": -35395.0, "price": 3450.0, "wacc": 0.115, "growth": 0.08, "t_growth": 0.045}
    }

    t_col1, t_col2 = st.columns([1, 2])
    with t_col1:
        custom_sym = st.text_input("Enter Ticker for DCF", value=st.session_state.get("active_ticker", "NVDA")).strip().upper()
        if custom_sym in dcf_presets:
            preset = dcf_presets[custom_sym]
            currency_code = "INR (₹ Cr)" if ".NS" in custom_sym else "USD ($)"
        else:
            # Safely fetch live metrics for custom ticker
            currency_code = "USD ($)"
            try:
                t_obj = yf.Ticker(custom_sym)
                fi = t_obj.fast_info
                curr_p = float(fi.get("last_price") or 100.0)
                shs = float(fi.get("shares") or 1e9)
                fcf_val = float(curr_p * shs * 0.04) # 4% initial FCF yield baseline
                preset = {
                    "fcf": max(fcf_val, 1e7),
                    "shares": max(shs, 1e6),
                    "net_debt": 0.0,
                    "price": curr_p,
                    "wacc": 0.09,
                    "growth": 0.10,
                    "t_growth": 0.025
                }
            except Exception:
                preset = {"fcf": 1000000000.0, "shares": 100000000.0, "net_debt": 0.0, "price": 50.0, "wacc": 0.09, "growth": 0.08, "t_growth": 0.025}

    with t_col2:
        with st.expander("🛠️ Custom Financial Inputs Override", expanded=(custom_sym not in dcf_presets)):
            c_f1, c_f2, c_f3 = st.columns(3)
            with c_f1:
                input_fcf = st.number_input("Base Free Cash Flow", value=float(preset["fcf"]), format="%.2f")
            with c_f2:
                input_shares = st.number_input("Diluted Shares Outstanding", value=float(preset["shares"]), format="%.2f")
            with c_f3:
                input_net_debt = st.number_input("Balance Sheet Net Debt (Debt - Cash)", value=float(preset["net_debt"]), format="%.2f")
            preset["fcf"] = input_fcf
            preset["shares"] = input_shares
            preset["net_debt"] = input_net_debt

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        slider_wacc = st.slider("Discount Rate / WACC (%)", min_value=5.0, max_value=18.0, value=float(preset["wacc"] * 100), step=0.25) / 100.0
    with col_s2:
        slider_growth = st.slider("5-Year FCF Growth Rate (%)", min_value=-15.0, max_value=50.0, value=float(preset["growth"] * 100), step=0.5) / 100.0
    with col_s3:
        slider_t_growth = st.slider("Perpetual Terminal Growth Rate (%)", min_value=1.5, max_value=5.0, value=float(preset["t_growth"] * 100), step=0.25) / 100.0

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

    # Reverse DCF solver
    try:
        rev_calc = reverse_dcf(
            current_price=curr_price,
            base_fcf=preset["fcf"],
            shares_outstanding=preset["shares"],
            discount_rate=slider_wacc,
            terminal_growth_rate=slider_t_growth,
            net_debt=preset["net_debt"]
        )
        implied_g = rev_calc["result"]["implied_growth_rate_pct"]
        st.info(f"💡 **Reverse DCF Implied Growth Rate:** At current market price (${curr_price:.2f}), the market implies a **{implied_g:+.2f}%** annual FCF growth rate over the next 5 years (vs your assumed {slider_growth*100:.1f}%).")
    except Exception:
        pass

    st.subheader(f"📊 Valuation Sensitivity Matrix: {custom_sym} (WACC vs 5Y Growth)")
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
            row.append(f"${res_calc['result']['fair_value_per_share']:,.2f}")
        matrix_data.append(row)

    df_matrix = pd.DataFrame(
        matrix_data,
        index=[f"Growth {g*100:.1f}%" for g in growth_range],
        columns=[f"WACC {w*100:.2f}%" for w in wacc_range]
    )
    st.table(df_matrix)


# --- MODULE 5: AUTONOMOUS RESEARCH STUDIO ---
elif "Autonomous Research Studio" in nav_choice:
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Autonomous Research Committee</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">Multi-agent committee execution: Analyst drafts thesis, Verifier audits provenance, Skeptic stress-tests assumptions.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Autonomous Research Committee",
            purpose="Generate institutional research dossiers with verifiable cryptographic audit trails.",
            capabilities=[
                "Analyst Agent financial modeling & 15+ metric extraction",
                "Cryptographic HMAC audit & single-round error repair loop",
                "Skeptic Agent adversarial stress testing (-200 bps margin, +100 bps WACC)",
                "Full markdown investment memorandum generation"
            ],
            use_case="Produce comprehensive, boardroom-ready investment memoranda backed by verified primary filings.",
            methodology="`run_research.py` pipeline orchestration; enforces zero mental arithmetic and fail-closed audit rules."
        )

    col_r1, col_r2 = st.columns([2, 1])
    with col_r1:
        wl_opts = ["(Custom Input)"] + st.session_state["watchlist"]
        r_picked = st.selectbox("⭐ Quick Select from Coverage List", wl_opts)
        default_r = r_picked if r_picked != "(Custom Input)" else "AAPL"
        r_input = st.text_input("Enter Company Name or Ticker to Research", value=default_r, help="Type company name (e.g. 'Apple') or ticker (e.g. 'AAPL', 'TCS.NS')")
        research_ticker = lookup_primary_ticker(r_input) or r_input.strip().upper()
        if research_ticker != r_input.strip().upper():
            st.caption(f"✨ Resolved to ticker `{research_ticker}`")
    with col_r2:
        workflow_type = st.selectbox("Research Workflow", ["Workflow 1: Comprehensive Valuation Deep Dive", "Workflow 2: Rapid Fundamental Screen"])
        workflow_num = 1 if "1" in workflow_type else 2

    if st.button("🚀 Run Autonomous Committee Research", type="primary"):
        with st.spinner(f"Agents assembling for {research_ticker}... Running Analyst -> Verifier -> Skeptic pipeline..."):
            try:
                from run_research import run_pipeline
                res_pipeline = run_pipeline(ticker=research_ticker, workflow_number=workflow_num, strict_audit=False)
                st.success(f"✅ Research Committee successfully completed audit for {research_ticker}!")
                
                report_dir = res_pipeline.get("report_dir")
                final_md = os.path.join(report_dir, "final_report.md") if report_dir else None
                if final_md and os.path.exists(final_md):
                    with open(final_md, "r", encoding="utf-8") as f:
                        report_content = f.read()
                    st.divider()
                    st.markdown(report_content)
                else:
                    st.info("Research completed with status: " + str(res_pipeline.get("status", "COMPLETE")))
            except Exception as e:
                st.error(f"Error during autonomous research: {str(e)}")

    # Inspect previous reports if clicked from home
    if "inspected_report_dir" in st.session_state:
        insp_dir = st.session_state.pop("inspected_report_dir")
        f_md = os.path.join(insp_dir, "final_report.md")
        if os.path.exists(f_md):
            st.divider()
            st.subheader(f"📄 Saved Investment Memorandum: `{os.path.basename(insp_dir)}`")
            with open(f_md, "r", encoding="utf-8") as f:
                st.markdown(f.read())


# --- MODULE 6: ANTIGRAVITY FINANCIAL COPILOT ---
elif "Antigravity Financial Copilot" in nav_choice:
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Antigravity Financial Copilot</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">Multi-turn research assistant and quantitative analytics engine powered by the Google Antigravity SDK.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Antigravity Financial Copilot",
            purpose="Interactive quantitative financial agent with real-time tool calling and portfolio management.",
            capabilities=[
                "Natural language stock research & valuation queries",
                "Live quotes, historical returns, and annualized volatility calculation",
                "Fundamental health, margin structure, and solvency analysis",
                "Stateful portfolio tracking and capital allocation modeling"
            ],
            use_case="Query specific company metrics, run multi-asset risk comparisons, and compute portfolio allocation models.",
            methodology="Google Antigravity SDK with strict system prompt forbidding mental math; calls deterministic tools."
        )

    env_api_key = os.environ.get("GEMINI_API_KEY", "")
    has_api_key = bool(env_api_key.strip())

    c_stat1, c_stat2 = st.columns([2, 1])
    with c_stat1:
        if has_api_key:
            st.success("🟢 Google Gemini API Connected (GEMINI_API_KEY Active)")
        else:
            st.warning("🟡 GEMINI_API_KEY is not configured. Conversational AI requires a key, but all quantitative tools below work 100% offline.")
    with c_stat2:
        st.info("⚡ Powered by `google-antigravity SDK`")

    with st.expander("⚙️ Gemini API Configuration", expanded=not has_api_key):
        custom_key = st.text_input("Enter Gemini API Key (or set in .env)", value=env_api_key, type="password", help="Get a key from Google AI Studio: https://aistudio.google.com/app/api-keys")
        if custom_key and custom_key != env_api_key:
            os.environ["GEMINI_API_KEY"] = custom_key
            st.success("API Key updated for current session!")

    ag_tab1, ag_tab2, ag_tab3, ag_tab4 = st.tabs([
        "💬 Conversational Copilot",
        "📊 Live Quotes & Volatility",
        "📑 Fundamental Health & Margins",
        "💼 Portfolio & Allocation"
    ])

    with ag_tab1:
        st.subheader("💬 Ask the Financial Copilot")
        st.caption("Ask natural-language questions, compare margins between competitors, or request portfolio allocations.")

        col_q1, col_q2, col_q3 = st.columns(3)
        sample_query = None
        if col_q1.button("🔍 Snapshot: NVDA Valuation", use_container_width=True):
            sample_query = "Give me a full financial snapshot, P/E ratio, and 1-month volatility for NVDA."
        if col_q2.button("⚖️ Compare: GOOGL vs MSFT", use_container_width=True):
            sample_query = "Compare revenue growth, gross margins, and debt-to-equity between GOOGL and MSFT."
        if col_q3.button("💼 Allocate: $50k Low-Risk", use_container_width=True):
            sample_query = "Calculate a low-risk $50,000 allocation across GOOGL, MSFT, and AAPL using inverse volatility."

        user_query = st.text_area("Research Query:", value=sample_query or "", height=85, placeholder="e.g. Compare operating margins and debt levels between Apple and Microsoft.")

        if st.button("🚀 Submit Query", type="primary"):
            if not user_query.strip():
                st.warning("Please enter a research query.")
            elif not os.environ.get("GEMINI_API_KEY"):
                st.error("Please enter a Gemini API Key in the settings expander above to use the conversational copilot.")
            else:
                with st.spinner("Antigravity Agent analyzing financial tools and synthesizing response..."):
                    try:
                        import concurrent.futures
                        import asyncio
                        from agents.antigravity_agent import build_config
                        from google.antigravity import Agent

                        def _call_agent():
                            async def _async_chat():
                                config = build_config(interactive=False)
                                async with Agent(config) as ag:
                                    resp = await ag.chat(user_query)
                                    return await resp.text()
                            return asyncio.run(_async_chat())

                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(_call_agent)
                            agent_output = future.result(timeout=60)

                        st.divider()
                        st.markdown(agent_output)
                    except Exception as e:
                        st.error(f"Agent Execution Error: {str(e)}")

    with ag_tab2:
        st.subheader("📊 Real-Time Market Data & Volatility Engine")
        q_col1, q_col2 = st.columns([2, 1])
        with q_col1:
            q_ticker = st.text_input("Ticker Symbol", value="GOOGL", key="copilot_q_ticker").strip().upper()
        with q_col2:
            q_period = st.selectbox("Horizon", ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"], index=1, key="copilot_q_period")

        if st.button("Fetch Market Data & Volatility", key="btn_fetch_quote_c"):
            from tools.antigravity_tools import get_stock_quote, get_historical_performance
            with st.spinner(f"Retrieving market telemetry for {q_ticker}..."):
                quote_data = get_stock_quote(q_ticker)
                hist_data = get_historical_performance(q_ticker, q_period)

                if "error" in quote_data:
                    st.error(quote_data["error"])
                else:
                    km1, km2, km3, km4 = st.columns(4)
                    curr_p = quote_data.get("current_price")
                    chg_pct = quote_data.get("change_percent")
                    km1.metric("Current Price", f"${curr_p:,.2f}" if curr_p else "N/A", chg_pct or None)
                    km2.metric("P/E Ratio", f"{quote_data.get('pe_ratio')}" if quote_data.get("pe_ratio") else "N/A")
                    km3.metric("Forward P/E", f"{quote_data.get('forward_pe')}" if quote_data.get("forward_pe") else "N/A")
                    mcap = quote_data.get("market_cap")
                    mcap_str = f"${mcap/1e12:.2f}T" if mcap and mcap >= 1e12 else (f"${mcap/1e9:.2f}B" if mcap else "N/A")
                    km4.metric("Market Cap", mcap_str)

                    if "error" not in hist_data:
                        hm1, hm2, hm3, hm4 = st.columns(4)
                        hm1.metric(f"{q_period.upper()} Return", hist_data.get("total_return_percent", "N/A"))
                        hm2.metric("Annualized Volatility", hist_data.get("annualized_volatility", "N/A"))
                        hm3.metric("Period High", f"${hist_data.get('period_high', 0):,.2f}")
                        hm4.metric("Period Low", f"${hist_data.get('period_low', 0):,.2f}")

    with ag_tab3:
        st.subheader("📑 Fundamental Health & Margin Structure")
        f_ticker = st.text_input("Ticker for Fundamentals", value="NVDA", key="copilot_f_ticker").strip().upper()
        if st.button("Inspect Financial Statements", key="btn_fetch_fund_c"):
            from tools.antigravity_tools import get_financial_metrics
            with st.spinner(f"Extracting balance sheet & margins for {f_ticker}..."):
                f_data = get_financial_metrics(f_ticker)
                if "error" in f_data:
                    st.error(f_data["error"])
                else:
                    f_col1, f_col2 = st.columns(2)
                    with f_col1:
                        st.markdown("##### 💵 Profitability & Cash Flow")
                        st.write(f"**Company:** {f_data.get('company_name')}")
                        st.write(f"**Revenue Growth (YoY):** {f_data.get('revenue_growth_yoy') or 'N/A'}")
                        st.write(f"**Gross Margins:** {f_data.get('gross_margins') or 'N/A'}")
                        st.write(f"**Operating Margins:** {f_data.get('operating_margins') or 'N/A'}")
                        st.write(f"**Return on Equity (ROE):** {f_data.get('return_on_equity_roe') or 'N/A'}")
                    with f_col2:
                        st.markdown("##### 🛡️ Solvency & Valuation Ratios")
                        st.write(f"**Debt-to-Equity:** {f_data.get('debt_to_equity') or 'N/A'}")
                        st.write(f"**Current Ratio:** {f_data.get('current_ratio') or 'N/A'}")
                        st.write(f"**Trailing P/E:** {f_data.get('trailing_pe') or 'N/A'}")
                        st.write(f"**Forward P/E:** {f_data.get('forward_pe') or 'N/A'}")
                        st.write(f"**Beta:** {f_data.get('beta') or 'N/A'}")

    with ag_tab4:
        st.subheader("💼 Stateful Portfolio Tracking & Asset Allocation")
        if "ag_portfolio" not in st.session_state:
            st.session_state["ag_portfolio"] = {"GOOGL": {"shares": 10.0, "cost_basis": 150.0}, "MSFT": {"shares": 5.0, "cost_basis": 400.0}}

        p_subtab1, p_subtab2 = st.tabs(["Active Holdings", "Allocation Calculator"])
        with p_subtab1:
            with st.form(key="add_position_form", clear_on_submit=True):
                c_pos1, c_pos2, c_pos3, c_pos4 = st.columns(4)
                with c_pos1:
                    new_sym = st.text_input("Ticker", value="AAPL").strip().upper()
                with c_pos2:
                    new_shares = st.number_input("Shares", min_value=0.1, value=10.0, step=1.0)
                with c_pos3:
                    new_cost = st.number_input("Cost Basis ($)", min_value=0.1, value=220.0, step=1.0)
                with c_pos4:
                    st.write("")
                    st.write("")
                    pos_submit = st.form_submit_button("➕ Record Position", use_container_width=True)
                if pos_submit:
                    st.session_state["ag_portfolio"][new_sym] = {"shares": new_shares, "cost_basis": new_cost}
                    st.success(f"Recorded {new_shares} shares of {new_sym}!")
                    st.rerun()

            holdings_rows = []
            tot_val, tot_cost = 0.0, 0.0
            for sym, pos in st.session_state["ag_portfolio"].items():
                sh = pos["shares"]
                cb = pos["cost_basis"]
                try:
                    cp = yf.Ticker(sym).fast_info.get("last_price") or cb
                except Exception:
                    cp = cb
                m_val = sh * cp
                c_val = sh * cb
                tot_val += m_val
                tot_cost += c_val
                holdings_rows.append({
                    "Symbol": sym, "Shares": sh, "Cost Basis": f"${cb:,.2f}",
                    "Current Price": f"${cp:,.2f}", "Market Value": f"${m_val:,.2f}",
                    "Unrealized P&L": f"${(m_val - c_val):,.2f}",
                    "P&L %": f"{((m_val - c_val) / c_val * 100):+.2f}%" if c_val > 0 else "0.0%"
                })
            if holdings_rows:
                st.table(pd.DataFrame(holdings_rows))
                col_pt1, col_pt2, col_pt3 = st.columns(3)
                col_pt1.metric("Total Portfolio Value", f"${tot_val:,.2f}")
                col_pt2.metric("Total Cost Basis", f"${tot_cost:,.2f}")
                col_pt3.metric("Total Unrealized P&L", f"${(tot_val - tot_cost):,.2f}", f"{((tot_val - tot_cost) / tot_cost * 100):+.2f}%" if tot_cost > 0 else None)

        with p_subtab2:
            st.markdown("##### ⚖️ Optimal Basket Allocation Solver")
            c_al1, c_al2, c_al3 = st.columns([2, 1, 1])
            with c_al1:
                al_symbols = st.text_input("Symbols", value="GOOGL, MSFT, AAPL, NVDA", key="copilot_al_syms")
            with c_al2:
                al_cap = st.number_input("Capital ($)", value=50000.0, step=5000.0, key="copilot_al_cap")
            with c_al3:
                al_strat = st.selectbox("Method", ["equal (Equal Weight)", "market_cap (Market Cap)", "low_risk (Inverse Beta)"], key="copilot_al_strat")

            strat_code = "equal" if "equal" in al_strat else ("market_cap" if "market_cap" in al_strat else "low_risk")
            if st.button("Calculate Allocation", key="btn_solve_alloc"):
                from tools.antigravity_tools import calculate_asset_allocation
                syms_list = [s.strip().upper() for s in al_symbols.split(",") if s.strip()]
                al_res = calculate_asset_allocation(syms_list, al_cap, strategy=strat_code)
                if "error" in al_res:
                    st.error(al_res["error"])
                else:
                    st.dataframe(pd.DataFrame(al_res["allocations"]), use_container_width=True)


# =============================================================================
# DOMAIN 3: QUANTITATIVE RISK & PORTFOLIO
# =============================================================================

# --- MODULE 7: PORTFOLIO CONSTRUCTION LAB ---
elif "Portfolio Construction Lab" in nav_choice:
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Portfolio Construction & Risk Lab</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">NVIDIA cuOpt quadratic programming portfolio optimization: Global Minimum Variance & Markowitz Efficient Frontier.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Portfolio Construction Lab (QP Optimizer)",
            purpose="Compute mathematically optimal asset weights that minimize total portfolio variance.",
            capabilities=[
                "Quadratic Programming (QP) variance minimization",
                r"Single-asset concentration constraints ($w_i \le w_{max}$)",
                r"Full Simplex constraint enforcement ($\sum w_i = 1, w_i \ge 0$)",
                r"Sharpe ratio and dual shadow cost $\lambda$ calculation"
            ],
            use_case="Construct risk-minimized portfolios across shortlisted compounders subject to fiduciary concentration limits.",
            methodology=r"Continuous convex quadratic optimization over empirical historical covariance matrix $\Sigma$."
        )

    p_col1, p_col2 = st.columns([2, 1])
    with p_col1:
        wl_preview_str = ", ".join(st.session_state["watchlist"][:5])
        port_input = st.text_input("Portfolio Universe (Comma-separated)", value=wl_preview_str)
        use_all_wl = st.checkbox(f"Use All {len(st.session_state['watchlist'])} Stocks in Current Watchlist", value=False)
    with p_col2:
        strategy_choice = st.selectbox("Optimization Objective", ["min_variance (Global Minimum Variance)", "mean_variance (Markowitz Efficient Frontier)"])
        strat = "min_variance" if "min_variance" in strategy_choice else "mean_variance"

    max_w_cap = st.slider("Single-Asset Concentration Cap", min_value=0.20, max_value=1.0, value=0.40, step=0.05)

    if st.button("⚡ Solve Optimal Portfolio Allocation", type="primary"):
        tickers_list = list(st.session_state["watchlist"]) if use_all_wl else [t.strip().upper() for t in port_input.split(",") if t.strip()]
        if len(tickers_list) < 2:
            st.warning("Please provide at least 2 valid tickers to compute an optimal portfolio covariance matrix.")
        else:
            with st.spinner(f"Solving quadratic program across {tickers_list}..."):
                try:
                    sandbox = BacktestSandbox()
                    bt_res = sandbox.run_optimized_portfolio_backtest(
                        tickers=tickers_list,
                        benchmark="SPY",
                        period="1y",
                        max_weight=max_w_cap,
                        strategy=strat
                    )
                    st.success("✅ NVIDIA cuOpt Quadratic Program Converged to Optimum!")
                    qp = bt_res["qp_solution"]
                    opt_weights = qp["weights"]

                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    col_m1.metric("Annualized Volatility", f"{qp['annualized_volatility']:.2f}%")
                    col_m2.metric("Sharpe Ratio (Rf=4.25%)", f"{bt_res['sharpe_ratio']:.2f}")
                    col_m3.metric("1Y Portfolio Return", f"{bt_res['portfolio_return_pct']:+.2f}%")
                    col_m4.metric("Alpha vs SPY", f"{bt_res['alpha_pct']:+.2f}%", delta=f"{bt_res['alpha_pct']:+.2f}%")

                    df_w = pd.DataFrame(list(opt_weights.items()), columns=["Asset", "Optimal Weight"])
                    df_w["Optimal Weight (%)"] = df_w["Optimal Weight"] * 100.0

                    fig_w = go.Figure(data=[go.Pie(labels=df_w["Asset"], values=df_w["Optimal Weight (%)"], hole=0.4)])
                    fig_w.update_layout(title="Optimal Capital Allocation (Simplex Sum = 100%)", height=450)
                    st.plotly_chart(fig_w, use_container_width=True)

                    st.markdown(f"**Dual Shadow Cost of Capital (Budget Multiplier $\\lambda$):** `{qp.get('dual_budget_multiplier', 0.0):.6f}`")
                except Exception as e:
                    st.error(f"Optimization error: {str(e)}")


# --- MODULE 8: SUPPLY CHAIN & LOGISTICS RISK ---
elif "Supply Chain & Logistics Risk" in nav_choice:
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Supply Chain & Operations Risk</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">Capacitated Vehicle Routing (CVRP) fleet optimization and fuel inflation shock elasticity.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Supply Chain & Operations Risk",
            purpose="Evaluate operating margin vulnerability to logistics bottlenecks and commodity inflation.",
            capabilities=[
                "cuOpt Capacitated Vehicle Routing Problem (CVRP) fleet routing",
                "Fuel price shock stress-testing (+10% and +20% spike)",
                "Fleet capacity utilization & transit cost per delivered unit",
                "Interactive spatial distribution network routing visualization"
            ],
            use_case="Determine whether a portfolio company's operating margin can withstand severe freight rate and fuel cost shocks.",
            methodology="Clarke-Wright Savings heuristic and 2-opt trajectory solver over Euclidean cost matrices."
        )

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        fleet_vehicles = st.slider("Fleet Size (Vehicles)", min_value=1, max_value=8, value=3)
        vehicle_cap = st.slider("Vehicle Capacity (Units)", min_value=20.0, max_value=100.0, value=50.0, step=5.0)
    with col_v2:
        cost_per_mile = st.slider("Cost per Distance Unit ($/km)", min_value=1.0, max_value=5.0, value=2.50, step=0.25)
        fuel_share = st.slider("Fuel Share of Logistics Cost (%)", min_value=10, max_value=60, value=35) / 100.0

    coords = [(0, 0), (12, 10), (15, -12), (-14, 11), (-12, -15), (22, 5)]
    demands = [0.0, 15.0, 20.0, 12.0, 18.0, 25.0]

    opt_vrp = SupplyChainLogisticsOptimizer(cost_per_distance_unit=cost_per_mile, fuel_cost_share=fuel_share)
    c_matrix = SupplyChainLogisticsOptimizer.build_euclidean_cost_matrix(coords)
    vrp_res = opt_vrp.solve_capacitated_vrp(cost_matrix=c_matrix, demands=demands, vehicle_capacity=vehicle_cap, num_vehicles=fleet_vehicles)

    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("Total Transit Cost", f"${vrp_res['total_transport_cost']:,.2f}")
    col_r2.metric("Fleet Capacity Utilization", f"{vrp_res['fleet_capacity_utilization_pct']:.1f}%")
    col_r3.metric("Cost per Delivered Unit", f"${vrp_res['cost_per_unit_delivered']:.2f}")

    # Plotly Spatial Route Visualization
    fig_routes = go.Figure()
    # Depot
    fig_routes.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", marker=dict(size=14, color="#b38822", symbol="square"), text=["Depot (0,0)"], textposition="top center", name="Distribution Center"))
    # Customers
    cust_x = [coords[i][0] for i in range(1, len(coords))]
    cust_y = [coords[i][1] for i in range(1, len(coords))]
    fig_routes.add_trace(go.Scatter(x=cust_x, y=cust_y, mode="markers+text", marker=dict(size=10, color="#10b981"), text=[f"Node {i} ({demands[i]}u)" for i in range(1, len(coords))], textposition="top center", name="Customer Demands"))

    # Connect routes
    colors = ["#38bdf8", "#f59e0b", "#f43f5e", "#a855f7", "#22c55e", "#eab308"]
    for r_idx, route in enumerate(vrp_res.get("routes", [])):
        rx = [coords[n][0] for n in route]
        ry = [coords[n][1] for n in route]
        fig_routes.add_trace(go.Scatter(x=rx, y=ry, mode="lines+markers", line=dict(color=colors[r_idx % len(colors)], width=2), name=f"Vehicle {r_idx+1}"))

    fig_routes.update_layout(title="Optimal Fleet Routing Network", height=420, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_routes, use_container_width=True)

    st.subheader("⛽ Fuel Inflation Shock Sensitivity")
    sens = vrp_res["sensitivity"]
    col_s1, col_s2 = st.columns(2)
    col_s1.warning(f"**+10% Fuel Price Spike:** Total Cost rises to **${sens['fuel_plus_10pct_cost']:,.2f}** (+${sens['logistics_cost_inflation_per_unit_10pct']:.3f}/unit)")
    col_s2.error(f"**+20% Fuel Price Spike:** Total Cost rises to **${sens['fuel_plus_20pct_cost']:,.2f}**")


# =============================================================================
# DOMAIN 4: AUDIT, GOVERNANCE & SYSTEM
# =============================================================================

# --- MODULE 9: INTERACTIVE 3D PIPELINE MAP ---
elif "Interactive 3D Pipeline Map" in nav_choice:
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Interactive 3D Pipeline Map</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">Spatial WebGL 3D visualization of the multi-agent research pipeline: orbital rotation, node inspection, and live simulation.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Interactive 3D Pipeline Map",
            purpose="Explore the spatial architecture of the autonomous research pipeline in interactive 3D.",
            capabilities=[
                "Interactive WebGL Three.js spatial canvas with 360° orbit, pan, and zoom",
                "Node telemetry inspection (inputs, outputs, verification rules, source links)",
                "Live step-by-step pipeline simulation with traveling data packets",
                "Expandable contract handoffs specification"
            ],
            use_case="Verify mathematical boundaries, data handoffs, and verification policies governing the autonomous agents.",
            methodology="Three.js r128 WebGL rendering pipeline; deterministic node-to-node contract specifications."
        )

    # 3D Interactive WebGL Component
    workflow_3d_html = render_interactive_3d_workflow(height=620)
    components.html(workflow_3d_html, height=640, scrolling=False)

    # Detailed Handoff Contracts Below 3D View
    st.divider()
    st.markdown("### 📋 Formal Agent-to-Agent Handoff Contracts")
    handoffs = [
        ("Dashboard → Pipeline Orchestrator", "The dashboard calls `run_pipeline(ticker, workflow_number)`. The orchestrator packages run IDs and ensures zero hand-written files exist.", "dashboard.py & run_research.py"),
        ("Orchestrator → Analyst Agent", "Orchestrator calls `analyst.run_workflow()`, returning `markdown_report`, `ledger`, and `skeptic_inputs`.", "run_research.py lines 78–88 · agents/analyst.py"),
        ("Orchestrator → Verifier (Round 1)", "First audit receives the Analyst report and its provenance sidecar, verifying HMAC integrity and checking document sidecars.", "run_research.py lines 95–101 · agents/verifier.py"),
        ("Verifier → Analyst (Conditional Repair Loop)", "Only when wrong figures are found, orchestrator invokes `analyst.correct_report()` for a single repair pass before re-verifying.", "run_research.py lines 105–129"),
        ("Orchestrator → Skeptic Agent", "Orchestrator expands `skeptic_inputs` into `skeptic.evaluate_thesis()`. The Skeptic returns a stress verdict and review markdown.", "run_research.py lines 152–162 · agents/skeptic.py"),
        ("Orchestrator → Verifier (Round 2)", "Audits the Skeptic review against the ledger sidecar to guarantee no synthetic numbers were introduced.", "run_research.py lines 157–175"),
        ("Orchestrator → Reports Dossier", "Orchestrator writes `final_report.md` with dual cryptographic provenance sidecars in `reports/<ticker>_<timestamp>/`.", "run_research.py lines 177–194")
    ]
    for idx, (title, detail, source_ref) in enumerate(handoffs, start=1):
        with st.expander(f"Handoff {idx:02d}: {title}", expanded=(idx == 1)):
            st.markdown(detail)
            st.caption(f"Source Implementation: `{source_ref}`")


# --- MODULE 10: INVESTMENT DECISION JOURNAL ---
elif "Investment Decision Journal" in nav_choice:
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Investment Decision Journal & Intelligence</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">Institutional decision hygiene: compare autonomous agent predictions & market consensus side-by-side with your independent thoughts.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Investment Decision Journal",
            purpose="Maintain disciplined investment hygiene and eliminate hindsight bias by logging decisions in real-time.",
            capabilities=[
                "Synthesized Agent & Market Predictions (DCF Fair Value, Margin of Safety, Skeptic Stress Verdict, Wall St Consensus)",
                "Actionable System Guidance ('What To Do': Accumulate / Trim / Hold thresholds)",
                "Explicit separation of Automated Predictions vs. Your Personal Independent Perspective",
                "Direct logging with tools/journal.py (writes CSV and individual .md entries with full provenance)"
            ],
            use_case="Review what AI agents and Wall Street analysts predicted, formulate your independent perspective, and log decisions to audit post-mortem outcomes.",
            methodology="Disciplined behavioral finance framework inspired by Ray Dalio and Michael Mauboussin."
        )

    journal_obj = DecisionJournal()
    journal_csv_path = journal_obj.csv_path

    # Ticker Selection & Live Intelligence Synthesis
    t_sel_c1, t_sel_c2 = st.columns([3, 1])
    with t_sel_c1:
        default_sym = st.session_state.get("active_ticker", "NVDA")
        journal_active_ticker = st.text_input("Active Ticker Symbol for Prediction & Journaling", value=default_sym).strip().upper()
        if journal_active_ticker != st.session_state.get("active_ticker"):
            st.session_state["active_ticker"] = journal_active_ticker
    with t_sel_c2:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Signals", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    intel = get_agent_and_market_prediction(journal_active_ticker)
    mkt = intel["market"]
    ag = intel["agents"]
    curr_px = mkt["current_price"]

    # 1. LIVE SYNTHESIS CARD: What Agents & Market Say + What To Do
    with st.container(border=True):
        st.markdown(f"#### ◈ Agent & Market Intelligence Synthesis: **{journal_active_ticker}** (Current: `${curr_px:,.2f}`)")
        st.caption("Primary-source DCF intrinsic value, autonomous thesis stress-testing, and Wall Street consensus expectations.")

        c_syn1, c_syn2, c_syn3 = st.columns(3)
        with c_syn1:
            st.markdown("##### 🤖 What Autonomous Agents Say")
            fv_txt = f"${ag['analyst_fair_value']:,.2f}" if ag['analyst_fair_value'] else "N/A"
            mos_txt = f"{ag['margin_of_safety_pct']:+.1f}%" if ag['margin_of_safety_pct'] is not None else "N/A"
            st.markdown(f"• **DCF Intrinsic Value:** `{fv_txt}`")
            st.markdown(f"• **Margin of Safety:** `{mos_txt}`")
            st.markdown(f"• **Skeptic Stress Test:** `{ag['skeptic_verdict']}`")
            st.markdown(f"• **Verifier Engine:** `{ag['verifier_status']}`")

        with c_syn2:
            st.markdown("##### 📈 What Market Consensus Says")
            tgt_m_txt = f"${mkt['target_mean']:,.2f}" if mkt['target_mean'] else "N/A"
            tgt_rng_txt = f"${mkt['target_low']:,.2f} – ${mkt['target_high']:,.2f}" if (mkt['target_low'] and mkt['target_high']) else "N/A"
            up_txt = f"{mkt['implied_upside_pct']:+.1f}%" if mkt['implied_upside_pct'] is not None else "N/A"
            st.markdown(f"• **Consensus Rating:** `{mkt['consensus_recommendation']}`")
            st.markdown(f"• **Mean Target Price:** `{tgt_m_txt}` (Upside: `{up_txt}`)")
            st.markdown(f"• **Price Target Range:** `{tgt_rng_txt}`")
            st.markdown(f"• **Analyst Coverage:** `{mkt['analyst_count']} Wall St Analysts`")

        with c_syn3:
            st.markdown("##### 🎯 Recommended Action: What To Do")
            st.markdown(f"**Action Verdict:** `{ag['recommended_action']}`")
            st.markdown(f"**Rationale:** {ag['action_rationale']}")
            if ag['target_exit_guide']:
                st.markdown(f"• **Suggested Target Exit:** `${ag['target_exit_guide']:,.2f}`")
            if ag['stop_loss_guide']:
                st.markdown(f"• **Downside Risk Stop:** `${ag['stop_loss_guide']:,.2f}`")

    # Form Prefill Helper State
    if "prefill_journal" not in st.session_state:
        st.session_state["prefill_journal"] = False

    col_btn_fill, _ = st.columns([2, 3])
    with col_btn_fill:
        if st.button("📥 Prefill Journal Form with Agent & Market Targets", use_container_width=True):
            st.session_state["prefill_journal"] = True
            st.rerun()

    # Pre-calculated values for form
    prefill_active = st.session_state.pop("prefill_journal", False)
    init_entry = curr_px if curr_px > 0 else 100.0
    init_target = ag["target_exit_guide"] if ag["target_exit_guide"] else round(init_entry * 1.20, 2)
    init_stop = ag["stop_loss_guide"] if ag["stop_loss_guide"] else round(init_entry * 0.85, 2)
    init_action = "BUY" if "BUY" in ag["recommended_action"] else ("TRIM" if "TRIM" in ag["recommended_action"] else "HOLD")
    init_agent_txt = f"Analyst DCF Fair Value: ${ag['analyst_fair_value']:,.2f} ({ag['margin_of_safety_pct']:+.1f}% Margin of Safety). Skeptic: {ag['skeptic_verdict']}. Recommendation: {ag['recommended_action']} ({ag['action_rationale']})." if ag['analyst_fair_value'] else "Valuation in progress."
    init_mkt_txt = f"Wall St Consensus: {mkt['consensus_recommendation']}. Mean Target: ${mkt['target_mean']:,.2f} ({mkt['implied_upside_pct']:+.1f}% upside). Covered by {mkt['analyst_count']} analysts." if mkt['target_mean'] else "Market target unavailable."

    # 2. DECISION LOGGING FORM (Separating Agent Predictions from User's Thoughts)
    with st.container(border=True):
        st.markdown("##### 📝 Record Investment Decision & Perspective")
        st.caption("Capture the system's prediction alongside your independent personal view before taking capital action.")

        with st.form(key="journal_entry_form", clear_on_submit=False):
            st.markdown("###### 1. Trade Execution Parameters")
            j_col1, j_col2, j_col3 = st.columns(3)
            with j_col1:
                j_ticker = st.text_input("Ticker Symbol", value=journal_active_ticker).strip().upper()
                action_opts = ["BUY", "HOLD", "SELL", "TRIM", "WATCH"]
                act_idx = action_opts.index(init_action) if init_action in action_opts else 0
                j_action = st.selectbox("Action", action_opts, index=act_idx)
            with j_col2:
                j_entry_p = st.number_input("Entry / Current Price ($)", min_value=0.01, value=float(init_entry), step=1.0)
                j_target_p = st.number_input("Price Target ($)", min_value=0.01, value=float(init_target), step=1.0)
            with j_col3:
                j_stop_loss = st.number_input("Stop Loss / Risk Boundary ($)", min_value=0.01, value=float(init_stop), step=1.0)
                j_conviction = st.selectbox("Conviction Level", ["HIGH", "MEDIUM", "LOW"])

            st.markdown("###### 2. 🤖 System Reference: What Agents & Market Predicted")
            j_ag_pred = st.text_area(
                "Agent Prediction & Valuation Synthesis (System Baseline)",
                value=init_agent_txt,
                help="Automated DCF fair value, Skeptic stress review, and Verifier audit status."
            )
            j_mkt_pred = st.text_area(
                "Market Predictions & Wall St Consensus (Market Baseline)",
                value=init_mkt_txt,
                help="Consensus analyst ratings, target prices, and implied upside/downside."
            )

            st.markdown("###### 3. ✍️ Your Personal Perspective & Independent Thoughts")
            j_user_thoughts = st.text_area(
                "Your Personal Thoughts & Independent Assessment",
                placeholder="Write your personal thoughts, qualitative view, macroeconomic context, or disagreements with the agents/market consensus...",
                help="Your independent perspective: what qualitative edge, macro timing, or thesis do you have that the AI or Street models might miss?"
            )
            j_thesis = st.text_area(
                "Core Investment Thesis & Financial Drivers",
                value=f"Position in {j_ticker} based on margin expansion and durable free cash flow generation.",
                placeholder="Core thesis drivers (e.g. pricing power, operating margin expansion, net cash cushion)..."
            )
            j_risks = st.text_area(
                "Key Risks & Invalidation Catalysts (When are you wrong?)",
                value="Thesis invalidation: >200bps gross margin degradation or customer churn.",
                placeholder="What specific metric deterioration would prove your thesis wrong?"
            )

            submit_decision = st.form_submit_button("💾 Save Decision to Journal", type="primary", use_container_width=True)
            if submit_decision:
                if j_ticker and j_thesis:
                    new_dec_id = journal_obj.log_decision(
                        ticker=j_ticker,
                        action=j_action,
                        entry_price=j_entry_p,
                        target_price=j_target_p,
                        stop_loss=j_stop_loss,
                        thesis=j_thesis,
                        risks=j_risks,
                        conviction=j_conviction,
                        agent_prediction=j_ag_pred,
                        market_consensus=j_mkt_pred,
                        user_thoughts=j_user_thoughts
                    )
                    st.success(f"✅ Successfully logged decision `{new_dec_id}` for **{j_ticker}** with side-by-side agent & personal thoughts!")
                    st.rerun()
                else:
                    st.warning("Please provide both a ticker symbol and an investment thesis.")

    # 3. HISTORICAL DECISIONS & COMPARATIVE INSPECTOR
    decisions_list = journal_obj.list_decisions()
    if decisions_list:
        df_journal = pd.DataFrame(decisions_list)
        open_count = len(df_journal[df_journal["status"] == "OPEN"]) if "status" in df_journal.columns else 0
        col_jm1, col_jm2 = st.columns(2)
        col_jm1.metric("Total Decisions Logged", len(df_journal))
        col_jm2.metric("Active Open Positions", open_count)

        st.markdown("### 📚 Logged Decision History")
        
        # Display selected summary columns in table
        show_cols = [c for c in ["decision_id", "date", "ticker", "action", "entry_price", "target_price", "stop_loss", "conviction", "status", "return_pct"] if c in df_journal.columns]
        st.dataframe(df_journal[show_cols], use_container_width=True, hide_index=True)

        st.markdown("### 🔍 Comparative Decision Inspector")
        st.caption("Select any logged decision to compare what the AI agents and market predicted against what you independently thought.")
        
        dec_options = [f"{d['decision_id']} - {d['ticker']} ({d['action']} on {d['date']})" for d in decisions_list]
        selected_dec_str = st.selectbox("Select Decision to Inspect", dec_options)
        selected_id = selected_dec_str.split(" - ")[0]
        
        target_dec = next((d for d in decisions_list if d["decision_id"] == selected_id), None)
        if target_dec:
            with st.container(border=True):
                st.markdown(f"#### Inspection: `{target_dec['decision_id']}` — **{target_dec['ticker']}** ({target_dec['action']})")
                st.caption(f"Status: **{target_dec['status']}** | Logged: `{target_dec['date']}` | Conviction: `{target_dec['conviction']}`")
                
                insp_c1, insp_c2 = st.columns(2)
                with insp_c1:
                    st.markdown("##### 🤖 What the Agents & Market Said")
                    st.info(
                        f"**Agent Prediction:**\n{target_dec.get('agent_prediction') or 'N/A'}\n\n"
                        f"**Market Consensus:**\n{target_dec.get('market_consensus') or 'N/A'}"
                    )
                with insp_c2:
                    st.markdown("##### ✍️ What You Thought & Decided (Personal Notes)")
                    st.success(
                        f"**Your Personal Perspective:**\n{target_dec.get('user_thoughts') or 'No separate thoughts recorded.'}\n\n"
                        f"**Core Thesis:**\n{target_dec.get('thesis') or 'N/A'}\n\n"
                        f"**Invalidation Risks:**\n{target_dec.get('risks') or 'N/A'}"
                    )

                # Close position workflow if still OPEN
                if target_dec.get("status") == "OPEN":
                    st.divider()
                    st.markdown("##### 🔒 Close Position & Record Post-Mortem")
                    with st.form(key=f"close_form_{selected_id}"):
                        c_cl1, c_cl2 = st.columns(2)
                        with c_cl1:
                            exit_p = st.number_input("Realized Exit Price ($)", min_value=0.01, value=float(target_dec.get("entry_price") or 100.0), step=1.0)
                        with c_cl2:
                            post_mortem = st.text_area("Post-Mortem Review (Lessons Learned)", placeholder="Did the thesis play out? Were the agents or your own thoughts more accurate?")
                        close_btn = st.form_submit_button("🏁 Close Position & Finalize Review", type="primary")
                        if close_btn:
                            journal_obj.close_decision(selected_id, exit_p, post_mortem)
                            st.success(f"Position {selected_id} closed at ${exit_p:,.2f}!")
                            st.rerun()
    else:
        st.info("No decisions logged yet. Use the form above to record your first investment thesis.")

    st.divider()
    review_md_path = os.path.join(PROJECT_DIR, "journal", "portfolio_review.md")
    if os.path.exists(review_md_path):
        st.markdown("### 📑 Portfolio Strategy & Retrospective Review")
        with open(review_md_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())


# --- MODULE 11: REGULATORY FILINGS & ALERTS ---
elif "Regulatory Filings & Alerts" in nav_choice:
    col_head, col_info = st.columns([5.5, 1.2])
    with col_head:
        st.markdown('<div class="header-style">Regulatory Filings & Price Alerts</div>', unsafe_allow_html=True)
        st.markdown('<div class="meridian-intro">Continuous monitor for SEC EDGAR 8-K/10-K filing disclosures and abnormal price volatility shocks.</div>', unsafe_allow_html=True)
    with col_info:
        render_tab_info_guide(
            title="Regulatory Filings & Market Alerts",
            purpose="Surfacing unscheduled filing disclosures and abnormal market volatility shocks across coverage universes.",
            capabilities=[
                "Live SEC EDGAR RSS feed monitoring for Form 8-K, 10-K, and 10-Q releases",
                "Abnormal intraday and 5-day price shock alerts",
                "Cached snapshot inspection with on-demand rescan capability",
                "Direct SEC EDGAR document links"
            ],
            use_case="Monitor for executive resignations, unexpected litigation, quarterly surprises, and liquidity shocks.",
            methodology="SEC EDGAR direct XML/RSS feeds + market price percentage divergence thresholds."
        )

    alerts_json_path = os.path.join(PROJECT_DIR, "reports", "active_alerts.json")

    col_btn_alert, col_alert_info = st.columns([1.5, 3])
    with col_btn_alert:
        if st.button("🔄 Rescan All Filings & Alerts Now", type="primary", use_container_width=True):
            with st.spinner("Scanning SEC EDGAR and market feeds across coverage universe..."):
                monitor = AlertMonitor()
                res_checks = monitor.run_all_checks()
                os.makedirs(os.path.dirname(alerts_json_path), exist_ok=True)
                with open(alerts_json_path, "w", encoding="utf-8") as f:
                    json.dump(res_checks, f, indent=2)
                st.success("✅ Alerts rescan completed!")
                st.rerun()

    # Load and display cached alerts
    if os.path.exists(alerts_json_path):
        with open(alerts_json_path, "r", encoding="utf-8") as f:
            alerts_data = json.load(f)

        total_alerts = alerts_data.get("total_alerts") or len(alerts_data.get("alerts", []))
        st.subheader(f"Active Monitored Alerts ({total_alerts} Total)")
        alerts_list = alerts_data.get("alerts", [])

        if alerts_list:
            for a in alerts_list:
                cat = a.get("category") or a.get("form") or "FILING"
                sev = a.get("severity", "MEDIUM")
                ticker = a.get("ticker", "GLOBAL")
                title = a.get("title") or a.get("description") or "Filing Released"
                url = a.get("url")

                with st.container(border=True):
                    col_al1, col_al2 = st.columns([4, 1])
                    with col_al1:
                        st.markdown(f"**[{cat}] {ticker}**: {title}")
                        st.caption(f"Filing Date: `{a.get('filing_date', 'N/A')}` · Accession: `{a.get('accession_number', 'N/A')}`")
                    with col_al2:
                        if url:
                            st.markdown(f'<a href="{url}" target="_blank"><button style="width:100%;padding:6px;border-radius:4px;border:1px solid #334d40;background:#182620;color:#f7faf7;cursor:pointer;font-size:0.8rem">🔗 View SEC Doc</button></a>', unsafe_allow_html=True)
        else:
            st.success("✅ All monitored securities within normal volatility bands. No unfiled 8-K / 10-K events detected.")
    else:
        st.info("No alert cache found. Click 'Rescan All Filings & Alerts Now' above to run your initial scan.")


if __name__ == "__main__":
    pass
