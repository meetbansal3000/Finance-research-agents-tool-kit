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
    page_title="Meridian | Equity Research",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Meridian design system
st.markdown("""
<style>
    :root {
        color-scheme: light;
        --ink:#18211e; --muted:#65716b; --pine:#1c2a25; --pine-soft:#2c4137;
        --paper:#f1efe6; --surface:#faf9f4; --white:#fffefa; --line:#d9ddd3;
        --line-dark:#33453b; --acid:#d6ed75; --positive:#26744d; --negative:#b34e43;
        --control-radius:7px; --panel-radius:10px;
    }
    html,body,[class*="css"] { font-family:"Segoe UI","Aptos",Arial,sans-serif; }
    .stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"] { color:var(--ink); background:var(--paper); }
    [data-testid="stHeader"] { background:rgba(241,239,230,.96); border-bottom:1px solid rgba(24,33,30,.08); }
    [data-testid="stToolbar"] { right:1.5rem; }
    .main .block-container { max-width:1480px; padding:1.6rem clamp(1rem,3.2vw,3rem) 3.5rem; }
    h1,h2,h3,h4 { color:var(--ink); letter-spacing:-.025em; }
    h1,.header-style { font-family:Georgia,"Times New Roman",serif; }
    h1 { font-size:clamp(1.8rem,3vw,2.8rem); font-weight:600; line-height:1.08; }
    h2 { font-size:clamp(1.25rem,2vw,1.55rem); font-weight:650; line-height:1.22; }
    h3 { font-size:1.08rem; font-weight:650; line-height:1.3; }
    .header-style { color:var(--ink); font-size:clamp(1.85rem,3vw,2.75rem); font-weight:600; line-height:1.08; letter-spacing:-.04em; margin:.1rem 0 .35rem; }
    .meridian-eyebrow { display:none; }
    .meridian-intro { color:var(--muted); font-size:.97rem; line-height:1.55; max-width:820px; margin:.25rem 0 1.35rem; }
    p,li { line-height:1.55; }
    [data-testid="stCaptionContainer"] { color:var(--muted); }
    [data-testid="stCaptionContainer"] p { line-height:1.45; }
    [data-testid="stVerticalBlock"] { gap:.85rem; }
    hr { border:0; border-top:1px solid var(--line); margin:1.2rem 0; }
    section[data-testid="stSidebar"] { background:var(--pine); border-right:1px solid #273a31; }
    section[data-testid="stSidebar"] > div { padding:.8rem .9rem 1.25rem; }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top:.6rem !important; }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] small,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color:#d0d9d2; }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] div[style*="Georgia"] { font-size:1.6rem !important; }
    section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,section[data-testid="stSidebar"] h4 { color:#f4f3ec; letter-spacing:-.01em; }
    section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] { gap:.32rem; }
    section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"] {
        position:relative; display:flex !important; align-items:center;
        width:100%; min-height:2.75rem; box-sizing:border-box;
        border:1px solid transparent; border-radius:var(--control-radius);
        padding:.5rem .7rem !important; color:#d5ddd6 !important;
        background:transparent !important;
        transition:background .14s ease,color .14s ease,border-color .14s ease;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:hover {
        background:rgba(255,255,255,.07) !important; border-color:rgba(255,255,255,.1);
        color:#fff !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"] > div:first-child > div[aria-hidden="true"] {
        width:.68rem !important; height:.68rem !important; min-width:.68rem !important;
        border:1px solid #809087 !important; border-radius:2px !important;
        background:transparent !important; box-shadow:none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) {
        background:var(--pine-soft) !important; border-color:#40564a !important;
        color:#f7f8f1 !important; box-shadow:inset 3px 0 0 var(--acid) !important;
        font-weight:700;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) [data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) [data-testid="stMarkdownContainer"] p {
        color:#f7f8f1 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) > div:first-child > div[aria-hidden="true"] {
        border-color:var(--acid) !important; background:var(--acid) !important;
        box-shadow:inset 0 0 0 2px var(--pine-soft) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label[data-baseweb="radio"]:focus-within {
        outline:2px solid var(--acid) !important; outline-offset:2px;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] { border:1px solid var(--line-dark); border-radius:var(--control-radius); background:rgba(255,255,255,.035); }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary { color:#eef1e9; }
    section[data-testid="stSidebar"] hr { border-color:var(--line-dark); }
    [data-testid="stMetric"] { background:transparent; border:0; border-bottom:1px solid var(--line); border-radius:0; padding:.55rem .1rem .8rem; box-shadow:none; }
    [data-testid="stMetricLabel"] { color:var(--muted); font-size:.78rem; font-weight:650; }
    [data-testid="stMetricValue"] { color:var(--ink); font-weight:680; letter-spacing:-.035em; }
    [data-testid="stMetricDelta"] { font-weight:650; }
    div[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line); border-radius:var(--panel-radius); background:var(--white); box-shadow:none; }
    div.stButton > button,[data-testid="stDownloadButton"] button {
        min-height:2.65rem; border:1px solid #aebbb0; border-radius:var(--control-radius);
        color:var(--ink); font-weight:650; background:var(--white);
        transition:background .14s ease,border-color .14s ease,transform .14s ease;
    }
    div.stButton > button:hover,[data-testid="stDownloadButton"] button:hover { border-color:var(--pine); background:#f2f3eb; transform:translateY(-1px); }
    div.stButton > button[kind="primary"] { background:var(--acid); border-color:var(--acid); color:var(--pine); }
    div.stButton > button[kind="primary"]:hover { background:#c8e45e; border-color:#c8e45e; }
    button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible,[role="slider"]:focus-visible { outline:3px solid #a6c43f !important; outline-offset:2px; }
    [data-baseweb="input"] > div,[data-baseweb="select"] > div,[data-baseweb="textarea"] > div { background:var(--white); border-color:#bfc8bd; border-radius:var(--control-radius); }
    [data-baseweb="input"] > div:focus-within,[data-baseweb="select"] > div:focus-within,[data-baseweb="textarea"] > div:focus-within { border-color:var(--pine); box-shadow:0 0 0 2px rgba(40,80,61,.12); }
    [data-testid="stSlider"] [role="slider"] { box-shadow:0 0 0 3px rgba(214,237,117,.45); }
    [data-testid="stCheckbox"] label,[data-testid="stRadio"] label { color:var(--ink); }
    [data-testid="stTabs"] [role="tablist"] { gap:.15rem; border-bottom:1px solid var(--line); }
    [data-testid="stTabs"] button[role="tab"] { min-height:2.7rem; padding:.45rem .8rem; color:var(--muted); font-weight:650; border-bottom-width:2px; }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color:var(--pine); border-bottom-color:var(--pine); }
    [data-testid="stExpander"] { border:1px solid var(--line); border-radius:var(--control-radius); background:rgba(255,254,250,.78); }
    [data-testid="stExpander"] summary { color:var(--ink); font-weight:650; }
    [data-testid="stDataFrame"],[data-testid="stTable"] { border:1px solid var(--line); border-radius:var(--control-radius); overflow:hidden; box-shadow:none; background:var(--white); }
    [data-testid="stPlotlyChart"] { border:1px solid var(--line); border-radius:var(--panel-radius); background:var(--white); padding:.1rem; box-shadow:none; }
    [data-testid="stAlert"] { border-radius:var(--control-radius); }
    .meridian-card { background:var(--white); border:1px solid var(--line); border-radius:var(--panel-radius); padding:1.05rem 1.15rem; height:100%; box-shadow:none; }
    .meridian-card:before { display:none; }
    .meridian-card-label { color:var(--muted); font-size:.72rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
    .meridian-card-value { color:var(--ink); font:600 1.8rem Georgia,"Times New Roman",serif; letter-spacing:-.035em; margin:.35rem 0 .15rem; }
    .meridian-card-note { color:var(--muted); font-size:.82rem; line-height:1.45; }
    .process-hierarchy { display:grid; gap:.7rem; margin:.8rem 0 1.4rem; }
    .process-root { background:var(--pine); color:#f4f3ec; border:1px solid var(--pine); border-radius:var(--panel-radius); padding:.9rem 1rem; text-align:center; box-shadow:none; }
    .process-root small { display:block; color:#c7d1ca; margin-top:.2rem; }
    .process-arrow { color:#70867a; font-size:1.1rem; line-height:1; text-align:center; }
    .process-row { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; }
    .process-node { background:var(--white); color:var(--ink); border:1px solid var(--line); border-radius:var(--control-radius); padding:.9rem 1rem; min-height:106px; box-shadow:none; }
    .process-node strong { display:block; font-size:.96rem; margin-bottom:.32rem; }
    .process-node span { display:block; color:var(--muted); font-size:.84rem; line-height:1.5; }
    .process-node .process-tag { display:inline-block; margin-top:.58rem; color:var(--pine); background:#eef3d8; border-radius:4px; padding:.16rem .42rem; font-size:.7rem; font-weight:700; }
    .process-support { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; }
    @media (max-width:800px) {
        .process-row,.process-support { grid-template-columns:1fr; }
        .main .block-container { padding:1.2rem .9rem 2.5rem; }
        [data-testid="stMetric"] { padding:.4rem .05rem .65rem; }
        .header-style { font-size:clamp(1.8rem,8vw,2.35rem); }
    }
    @media (prefers-reduced-motion:reduce) { *,*::before,*::after { scroll-behavior:auto !important; transition-duration:.01ms !important; animation-duration:.01ms !important; } }
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
st.sidebar.markdown("<div style='font:600 1.45rem Georgia,serif;color:#f7faf7;letter-spacing:-.03em'>◈ Meridian</div><div style='color:#aebdb2;font-size:.78rem;margin:.15rem 0 1rem'>Equity research workspace</div>", unsafe_allow_html=True)
st.sidebar.caption("Primary-source research · verified analysis")

if "pending_page" in st.session_state:
    st.session_state["active_page"] = st.session_state.pop("pending_page")

nav_choice = st.sidebar.radio(
    "WORKSPACE",
    [
        "⌂  Overview",
        "↘  Process map",
        "▦  Finance playbooks",
        "◎  Watchlist",
        "◒  Markets & charts",
        "◇  Valuation",
        "✦  Research studio",
        "▤  Portfolio lab",
        "↗  Supply chain",
        "▧  Decision journal",
        "◉  Alerts & filings"
    ],
    key="active_page"
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
if nav_choice == "⌂  Overview":
    st.markdown('<div class="header-style">Research, in one place.</div>', unsafe_allow_html=True)
    st.markdown('<div class="meridian-intro">Follow your coverage, open recent dossiers, or start a research task.</div>', unsafe_allow_html=True)

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
        ("Coverage list", str(len(st.session_state["watchlist"])), "Companies on your active watchlist"),
        ("Research dossiers", str(len(report_dirs)), "Completed reports saved in this workspace"),
        ("Latest update", latest_date, "Based on the most recently saved dossier"),
    ]
    for col, (label, value, note) in zip(stat_cols, overview_stats):
        with col:
            st.markdown(
                f'<div class="meridian-card"><div class="meridian-card-label">{label}</div>'
                f'<div class="meridian-card-value">{value}</div><div class="meridian-card-note">{note}</div></div>',
                unsafe_allow_html=True
            )

    st.markdown("### Start with a task")
    action_cols = st.columns(3)
    quick_actions = [
        ("✦  Start a research review", "Run the analyst, verification, and skeptic workflow.", "✦  Research studio"),
        ("◎  Review your watchlist", "Compare coverage and shortlist candidates.", "◎  Watchlist"),
        ("◇  Explore a valuation", "Adjust DCF assumptions and view sensitivity.", "◇  Valuation"),
    ]
    for col, (title, detail, target_page) in zip(action_cols, quick_actions):
        with col:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(detail)
                if st.button("Open", key=f"home_{target_page}", use_container_width=True):
                    st.session_state["pending_page"] = target_page
                    st.rerun()

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("### Recent research")
        if report_dirs:
            for entry in report_dirs[:5]:
                ticker_label = entry.name.rsplit("_", 1)[0] if len(entry.name) > 11 else entry.name
                updated = datetime.datetime.fromtimestamp(entry.stat().st_mtime).strftime("%d %b %Y")
                st.markdown(f"**{ticker_label}** · {updated}  \n`reports/{entry.name}/final_report.md`")
        else:
            st.info("Your completed dossiers will appear here after a research run.")
    with right:
        st.markdown("### Active coverage")
        if st.session_state["watchlist"]:
            st.write(" · ".join(f"`{ticker}`" for ticker in st.session_state["watchlist"]))
        else:
            st.info("Your watchlist is empty. Add a company to begin tracking it.")
        st.caption("Financial figures in research reports retain their source and audit trail. Market feeds may be delayed.")

elif nav_choice == "↘  Process map":
    st.markdown('<div class="header-style">How research moves through Meridian</div>', unsafe_allow_html=True)
    st.markdown('<div class="meridian-intro">Follow the handoffs, verification steps, and saved outputs from request to final report.</div>', unsafe_allow_html=True)

    st.markdown("### Hierarchy")
    st.markdown("""
    <div class="process-hierarchy">
      <div class="process-root"><strong>Researcher</strong><small>Chooses a company and a workflow</small></div>
      <div class="process-arrow">↓</div>
      <div class="process-root"><strong>Meridian dashboard</strong><small>Collects the ticker and starts the research run</small></div>
      <div class="process-arrow">↓</div>
      <div class="process-root"><strong>Pipeline orchestrator · <code>run_research.run_pipeline</code></strong><small>Controls the order, passes data between agents, and writes the final dossier</small></div>
      <div class="process-arrow">↓ calls each stage</div>
      <div class="process-row">
        <div class="process-node"><strong>1 · Analyst</strong><span>Retrieves filing and market data, calculates metrics, records provenance, and drafts the report.</span><span class="process-tag">Returns report + skeptic_inputs</span></div>
        <div class="process-node"><strong>2 · Verifier · both reports</strong><span>Audits the Analyst report before the Skeptic runs, then audits the Skeptic review before synthesis.</span><span class="process-tag">Returns audit + wrong_items</span></div>
        <div class="process-node"><strong>3 · Skeptic</strong><span>Stress-tests assumptions using the structured inputs prepared by the Analyst.</span><span class="process-tag">Returns verdict + review</span></div>
      </div>
      <div class="process-arrow">↓ uses shared tools · saves outputs</div>
      <div class="process-support">
        <div class="process-node"><strong>Evidence tools</strong><span>FilingExtractor, DataLayer, calculation functions, and the provenance ledger.</span></div>
        <div class="process-node"><strong>Reports and audit trail</strong><span>Analyst and skeptic markdown, verification results, and JSON provenance sidecars in <code>reports/</code>.</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.info("Agents communicate through direct Python method calls and returned dictionaries. There is no separate agent chat loop or message broker in this pipeline.")

    st.markdown("### What each handoff carries")
    handoffs = [
        ("Dashboard → pipeline", "The dashboard calls `run_pipeline(ticker, workflow_number)`. The pipeline resolves the ticker and creates the report folder.", "dashboard.py lines 582–589 · run_research.py lines 37–75", "dashboard.py#L582-L589"),
        ("Pipeline → Analyst → pipeline", "`run_workflow()` returns `markdown_report`, its `ledger`, `metrics`, and `skeptic_inputs` as a Python dictionary.", "run_research.py lines 78–88 · agents/analyst.py lines 1310–1344", "run_research.py#L78-L88"),
        ("Pipeline → Verifier → pipeline", "The first audit receives the Analyst report and its provenance sidecar, then returns an audit summary and any wrong or unverifiable claims. Independent source refetch is enabled by the pipeline default.", "run_research.py lines 95–101 · agents/verifier.py line 533", "run_research.py#L95-L101"),
        ("Verifier → Analyst · conditional", "Only when wrong figures are found, the orchestrator passes `wrong_items`, the report text, and the ledger to `correct_report()`, then audits once more.", "run_research.py lines 105–129 · agents/analyst.py lines 1356–1365", "run_research.py#L105-L129"),
        ("Pipeline → Skeptic → pipeline", "The orchestrator expands `skeptic_inputs` into `evaluate_thesis(...)`. The Skeptic returns a verdict, review markdown, and its own ledger.", "run_research.py lines 152–162 · agents/analyst.py lines 1310–1344", "run_research.py#L152-L162"),
        ("Pipeline → Verifier · Skeptic audit", "After saving the Skeptic review and its sidecar, the orchestrator creates a second Verifier and audits that review before synthesis.", "run_research.py lines 157–175", "run_research.py#L157-L175"),
        ("Pipeline → reports → dashboard", "The orchestrator saves the final dossier and sidecars; the dashboard opens `final_report.md` and displays it.", "run_research.py lines 177–194 · dashboard.py lines 586–595", "run_research.py#L177-L194"),
    ]
    source_base = "https://github.com/meetbansal3000/Finance-research-agents-tool-kit/blob/5065a97a5685eed92abbfb0f0b9584145b4eb47e/"
    for idx, (title, detail, source_label, source_path) in enumerate(handoffs, start=1):
        with st.expander(f"{idx:02d}  {title}", expanded=(idx == 1)):
            st.markdown(detail)
            st.markdown(f"[{source_label}]({source_base + source_path})")

    nvidia_col, correction_col = st.columns(2)
    with nvidia_col:
        with st.container(border=True):
            st.markdown("**Optional · NVIDIA NIM**")
            st.caption("The Skeptic can request an NVIDIA NIM critique when `enable_nvidia=True`. The dashboard call leaves this flag at its default `False`.")
            st.markdown(f"[Skeptic condition · agents/skeptic.py lines 699–714]({source_base}agents/skeptic.py#L699-L714)")
    with correction_col:
        with st.container(border=True):
            st.markdown("**Evidence stays attached**")
            st.caption("Analyst and Skeptic each keep a ledger; the orchestrator saves those as JSON sidecars beside their reports.")
            st.markdown(f"[Ledger sidecars · run_research.py lines 83–88]({source_base}run_research.py#L83-L88)")

elif nav_choice == "◎  Watchlist":
    st.markdown('<div class="header-style">Company coverage</div>', unsafe_allow_html=True)
    st.markdown('<div class="meridian-intro">Compare fundamental signals and manage the companies in your watchlist.</div>', unsafe_allow_html=True)

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
elif "Markets & charts" in nav_choice:
    st.markdown('<div class="header-style">Markets & charts</div>', unsafe_allow_html=True)
    st.markdown('<div class="meridian-intro">Explore price action, technical summaries, company financials, and historical market data.</div>', unsafe_allow_html=True)

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
elif nav_choice == "◇  Valuation":
    st.markdown('<div class="header-style">Valuation model</div>', unsafe_allow_html=True)
    st.markdown('<div class="meridian-intro">Adjust core assumptions and inspect how growth and discount rates shape the model output.</div>', unsafe_allow_html=True)

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
elif nav_choice == "✦  Research studio":
    st.markdown('<div class="header-style">Research committee</div>', unsafe_allow_html=True)
    st.markdown('<div class="meridian-intro">Run the Analyst, Verifier, and Skeptic workflow, then review the source-backed investment memorandum.</div>', unsafe_allow_html=True)

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
elif nav_choice == "▤  Portfolio lab":
    st.markdown('<div class="header-style">Portfolio construction</div>', unsafe_allow_html=True)
    st.markdown('<div class="meridian-intro">Choose a stock universe and strategy to calculate a portfolio allocation.</div>', unsafe_allow_html=True)

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
elif nav_choice == "↗  Supply chain":
    st.markdown('<div class="header-style">Supply chain economics</div>', unsafe_allow_html=True)
    st.markdown('<div class="meridian-intro">Explore fleet routing costs, capacity use, and the impact of fuel price shocks on delivery economics.</div>', unsafe_allow_html=True)

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
elif nav_choice == "▧  Decision journal":
    st.markdown('<div class="header-style">Decision journal</div>', unsafe_allow_html=True)
    st.markdown('<div class="meridian-intro">Review logged investment decisions and the latest portfolio review in one place.</div>', unsafe_allow_html=True)

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
elif nav_choice == "◉  Alerts & filings":
    st.markdown('<div class="header-style">Filings & price alerts</div>', unsafe_allow_html=True)
    st.markdown('<div class="meridian-intro">Review saved alerts or check monitored companies for market and filing events.</div>', unsafe_allow_html=True)

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



# =============================================================================
# VIEW 9: OPENACCOUNTANT FINANCE PLAYBOOKS
# =============================================================================
elif nav_choice == "▦  Finance playbooks":
    from tools.finance_playbooks import load_openaccountant_playbooks

    playbooks = load_openaccountant_playbooks()
    st.markdown('<div class="header-style">Finance playbooks</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="meridian-intro">Browse the OpenAccountant guides installed in this workspace, with their inputs and tool requirements.</div>',
        unsafe_allow_html=True,
    )

    if not playbooks:
        st.warning("No OpenAccountant playbooks were found in the project skill lockfile.")
    else:
        st.info(
            f"{len(playbooks)} playbooks are installed for Codex in this workspace. "
            "They are Markdown workflows, not executable app features. This dashboard has no Wilson transaction store, bank sync, or Plaid connector."
        )

        filter_col, search_col = st.columns([1, 2])
        with filter_col:
            categories = ["All categories"] + sorted({item["category"] for item in playbooks})
            chosen_category = st.selectbox("Category", categories, key="finance_playbook_category")
        with search_col:
            search_text = st.text_input(
                "Find a playbook",
                placeholder="Search by name or topic",
                key="finance_playbook_search",
            ).strip().casefold()

        filtered = [
            item for item in playbooks
            if (chosen_category == "All categories" or item["category"] == chosen_category)
            and (not search_text or search_text in item["name"].casefold() or search_text in item["description"].casefold() or search_text in item["slug"])
        ]

        if not filtered:
            st.info("No playbooks match those filters.")
        else:
            selected_slug = st.selectbox(
                f"Choose from {len(filtered)} playbooks",
                options=[item["slug"] for item in filtered],
                format_func=lambda slug: next(item["name"] for item in filtered if item["slug"] == slug),
                key="finance_playbook_selected",
            )
            selected = next(item for item in filtered if item["slug"] == selected_slug)

            st.subheader(selected["name"])
            st.write(selected["description"])
            status_col, category_col = st.columns(2)
            with status_col:
                st.metric("Availability in this app", "Read-only guide")
            with category_col:
                st.metric("Collection", selected["category"])

            if selected["pro_required"]:
                st.warning("This playbook describes Wilson Pro or Plaid setup. Neither integration is configured in this app.")
            elif selected["wilson_tools"]:
                st.caption("Wilson tool calls are documented in this guide but are unavailable in this app.")
            else:
                st.caption("Use the steps as a manual reference; this page does not execute the workflow.")

            if selected["wilson_tools"]:
                st.markdown("**Tools referenced by the playbook**")
                st.write(" · ".join(f"`{tool}`" for tool in selected["wilson_tools"]))

            if selected["manual_workflow"]:
                with st.expander("Manual workflow", expanded=True):
                    st.markdown(selected["manual_workflow"])
            with st.expander("Full playbook", expanded=False):
                st.markdown(selected["body"])

            source_url = f"https://github.com/openaccountant/skills/blob/main/{selected['source_path']}"
            st.markdown(f"[View source playbook on GitHub]({source_url})")

        st.divider()
        st.caption(
            "The installed files live in `.agents/skills` and are discoverable by Codex agents working in this repository. "
            "The app’s Python research agents do not automatically execute these bookkeeping workflows; the existing Analyst, Verifier, and Skeptic pipeline remains unchanged."
        )


if __name__ == "__main__":
    pass


