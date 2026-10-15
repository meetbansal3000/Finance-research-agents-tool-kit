"""
tools/meridian_desk_ui.py
Institutional Streamlit Web Terminal Module for Meridian Multi-Asset Master Orchestrator:
1. Master Orchestrator Committee Synthesis & Risk Gatekeeper
2. Options Greek Strategist (Black-Scholes Greeks, IV skew, Multi-Leg Strategy Payoffs)
3. Futures & Commodity Desk (Term Structure, Contango/Backwardation, Roll Yields, Margin Buffers)
4. Fixed Income Macro Agent (Treasury Yield Curve Inversion, Duration, Convexity, DV01, Rate Shocks)
5. Crypto & 24/7 Derivatives Agent (Perpetual Funding APY, Basis Arbitrage, Liquidation Cascade Risk)
6. Cross-Asset Risk Officer (Parametric VaR, CVaR, Crisis Stress Matrix, Master Red Flags Registry)
"""

import json
import datetime
from typing import Dict, Any, List, Optional
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from agents.meridian_orchestrator import MeridianMultiAssetOrchestrator
from agents.options_greek_agent import OptionsGreekStrategist
from agents.futures_commodity_agent import FuturesCommodityAgent
from agents.fixed_income_macro_agent import FixedIncomeMacroAgent
from agents.crypto_derivatives_agent import CryptoDerivativesAgent
from agents.cross_asset_risk_officer import CrossAssetRiskOfficer
from tools.calc.derivatives_math import (
    BlackScholesEngine,
    FuturesCommodityEngine,
    FixedIncomeMacroEngine,
    CryptoDerivativesEngine,
    CrossAssetRiskEngine
)
from tools.calc.probability_simulator import (
    EconometricProbabilitySimulator,
    cornish_fisher_quantile,
    hitting_time_touch_probability,
    calculate_kelly_fraction
)
from plotly.subplots import make_subplots
import yfinance as yf
from tools.ticker_search import lookup_primary_ticker, search_company_tickers
from tools.data_layer import get_data_layer
from tools.multi_asset_data import MultiAssetDataEngine
from tools.paper_trading import get_paper_trading_engine, INITIAL_PORTFOLIO_CASH
from tools.broker_client import ExecutionCostModel, MultiExchangeRouter, AlpacaBrokerClient, InteractiveBrokersClient
from tools.alert_dispatcher import get_alert_dispatcher, WebhookAlertDispatcher
from tools.calc.walk_forward_backtest import WalkForwardBacktester, AlgoOpportunityScanner
from tools.backtest import BacktestSandbox


@st.cache_data(ttl=60, show_spinner=False)
def resolve_and_fetch_live_asset(query_str: str) -> Dict[str, Any]:
    """
    Intelligently resolves informal company names (e.g. 'micron', 'apple', 'nvidia', 'tesla')
    or direct tickers ('MU', 'AAPL', 'NVDA') to official symbols, company metadata,
    and real-time market prices, ATM strikes, and implied volatilities.
    """
    clean_q = (query_str or "").strip()
    if not clean_q:
        return {
            "query": "", "symbol": "MU", "name": "Micron Technology, Inc.",
            "exchange": "NASDAQ", "type": "EQUITY", "price": 100.0, "change_pct": 0.0,
            "currency": "USD", "atm_strike": 100.0, "atm_iv_pct": 35.0, "dte": 30,
            "expirations": [], "selected_expiry": "", "pcr_oi": 1.0, "resolved": False
        }

    # 1. Primary symbol resolution via ticker search engine
    sym = lookup_primary_ticker(clean_q) or clean_q.upper()
    sym = sym.strip().upper()

    # 2. Company name and exchange lookup
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

    # 3. Real-time market price lookup
    price = 0.0
    change_pct = 0.0
    currency = "USD"
    try:
        dl = get_data_layer()
        q = dl.get_quote(sym)
        if q and q.get("price") is not None and float(q["price"]) > 0:
            price = float(q["price"])
            currency = q.get("currency", "USD")
    except Exception:
        pass

    if price <= 0.0:
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

    # 4. Live Options Chain & Implied Volatility
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
                try:
                    exp_date = datetime.date.fromisoformat(selected_expiry)
                    dte = max(1, (exp_date - datetime.date.today()).days)
                except Exception:
                    dte = 30

            # Find ATM contract IV
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


@st.cache_data(ttl=1800, show_spinner=False)
def get_cached_empirical_moments(symbol: str) -> Dict[str, Any]:
    """
    Caches 252-day empirical higher moments calculation (drift, volatility,
    skewness, excess kurtosis, Jarque-Bera) for 30 minutes to ensure snappy UI interaction.
    """
    engine = EconometricProbabilitySimulator()
    return engine.calculate_empirical_moments(symbol)


def render_meridian_multi_asset_desk():
    """Renders the comprehensive institutional Meridian Multi-Asset Web Terminal."""

    # Top Brand & Topology Banner
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0e1520 0%, #131c2b 100%); border: 1px solid #1E293B; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
            <div>
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:22px; color:#38BDF8;">◈</span>
                    <span style="font-size:1.45rem; font-weight:800; color:#F8FAFC; letter-spacing:-0.02em;">MERIDIAN MULTI-ASSET MASTER ORCHESTRATOR</span>
                </div>
                <div style="font-size:0.85rem; color:#94A3B8; margin-top:4px;">
                    Institutional Multi-Desk Autonomous Execution · Quantitative Derivatives, Macro Rates, Commodities, 24/7 Crypto, and Cross-Asset Risk Gatekeeping
                </div>
            </div>
            <div style="display:flex; gap:8px; align-items:center;">
                <span style="background:rgba(56,189,248,0.12); border:1px solid rgba(56,189,248,0.3); color:#38BDF8; font-size:0.75rem; font-weight:700; padding:4px 10px; border-radius:9999px;">
                    ● 5 DESKS ACTIVE
                </span>
                <span style="background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); color:#34D399; font-size:0.75rem; font-weight:700; padding:4px 10px; border-radius:9999px;">
                    ◈ HMAC-SHA256 AUDITED
                </span>
            </div>
        </div>
        <div style="margin-top:16px; background:#0B0E14; border:1px solid #1E2638; border-radius:6px; padding:12px 16px; font-family:monospace; font-size:0.76rem; color:#CBD5E1; overflow-x:auto;">
┌─────────────────────────────────────────────────────────────────────────────┐<br>
│                    MERIDIAN MULTI-ASSET MASTER ORCHESTRATOR                 │<br>
└──────┬───────────────┬──────────────┬──────────────┬──────────────┬─────────┘<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼<br>
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐<br>
│Options Greek ││Futures &amp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;││Fixed Income&nbsp;&nbsp;││Crypto &amp; 24/7 ││Cross-Asset&nbsp;&nbsp;&nbsp;│<br>
│Strategist&nbsp;&nbsp;&nbsp;&nbsp;││Commodity&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;││Macro Agent&nbsp;&nbsp;&nbsp;││Derivatives&nbsp;&nbsp;&nbsp;││Risk Officer&nbsp;&nbsp;│<br>
│&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;││Desk Agent&nbsp;&nbsp;&nbsp;&nbsp;││&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;││Agent&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;││&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│<br>
└──────────────┘└──────────────┘└──────────────┘└──────────────┘└──────────────┘
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Initialize Orchestrator in session state if missing
    if "meridian_orchestrator" not in st.session_state:
        st.session_state["meridian_orchestrator"] = MeridianMultiAssetOrchestrator()
    orchestrator: MeridianMultiAssetOrchestrator = st.session_state["meridian_orchestrator"]

    # Initialize Institutional Multi-Exchange Order Router in session state
    if "multi_exchange_router" not in st.session_state:
        st.session_state["multi_exchange_router"] = MultiExchangeRouter(active_mode="SIMULATION_PAPER")
    router: MultiExchangeRouter = st.session_state["multi_exchange_router"]

    # 8 Specialized Sub-Tabs
    tab_orch, tab_opt, tab_prob, tab_fut, tab_fi, tab_crypto, tab_risk, tab_bt = st.tabs([
        "🏛️ Master Orchestrator",
        "🎯 Options Greek Strategist",
        "🎲 Econometric Probability Simulator",
        "🌾 Futures & Commodity Desk",
        "📈 Fixed Income Macro Agent",
        "⚡ Crypto & 24/7 Derivatives",
        "🛡️ Cross-Asset Risk Officer & Red Flags",
        "📊 Walk-Forward Backtest & Algo Engine"
    ])

    # =========================================================================
    # TAB 1: MASTER ORCHESTRATOR (Multi-Desk Committee Review)
    # =========================================================================
    with tab_orch:
        st.markdown("### 🏛️ Institutional Multi-Asset Committee Review")
        st.caption("Coordinate execution across all 5 specialized desks, aggregate portfolio risk, and enforce independent CRO gatekeeping.")

        with st.expander("📐 Mathematical Formulations & Multi-Desk Synthesis Audit", expanded=False):
            st.markdown(r"""
            #### 🧮 Multi-Desk Capital Allocation & Synthesis Mathematics
            - **Simplex Capital Budget Constraint**:
              $$\sum_{i=1}^M \text{Allocation}_i = \text{Total Capital} \quad (\sum w_i = 1)$$
            - **Cross-Asset Portfolio Variance**:
              $$\sigma_p^2 = \mathbf{w}^T \mathbf{\Sigma} \mathbf{w} = \sum_{i=1}^M \sum_{j=1}^M w_i w_j \sigma_i \sigma_j \rho_{ij}$$
            - **Parametric 1-Day 99% Value-at-Risk (VaR)**:
              $$\text{VaR}_{99\%} = z_{0.99} \cdot \sigma_p \cdot \sqrt{\frac{1}{252}} \cdot \text{Capital} \quad (z_{0.99} \approx 2.3263)$$
            - **Parametric 1-Day 99% Expected Shortfall (CVaR)**:
              $$\text{CVaR}_{99\%} = \frac{\phi(z_{0.99})}{1 - 0.99} \cdot \sigma_p \cdot \sqrt{\frac{1}{252}} \cdot \text{Capital}$$
            - **CRO Gatekeeper Rule**:
              $$\text{Verdict} = \begin{cases} \text{REJECTED (VETO)}, & \text{if } \text{Critical Flags} > 0 \text{ or } \text{VaR}_{99\%} > 4.5\% \\ \text{CONDITIONAL APPROVAL}, & \text{if } \text{High Flags} > 0 \\ \text{APPROVED}, & \text{otherwise} \end{cases}$$
            """)

        # ---------------------------------------------------------------------
        # 1. LIVE PAPER TRADING PORTFOLIO & REAL-DEAL POSITIONS BOOK
        # ---------------------------------------------------------------------
        st.markdown("### 💼 Live Trading Portfolio ($1,000,000 Capital Balance)")
        st.caption("Real-time mark-to-market valuations, live cash tracking, and open deals execution ledger.")

        paper_engine = get_paper_trading_engine()
        port = paper_engine.load_portfolio()
        open_positions = port.get("positions", [])
        closed_trades = port.get("closed_trades", [])

        # Executive KPI Cards
        tot_equity = float(port.get("total_equity", INITIAL_PORTFOLIO_CASH))
        cash_bal = float(port.get("cash_balance", INITIAL_PORTFOLIO_CASH))
        open_val = float(port.get("total_open_value", 0.0))
        unreal_pnl = float(port.get("total_unrealized_pnl", 0.0))
        real_pnl = float(port.get("total_realized_pnl", 0.0))
        ret_pct = float(port.get("portfolio_return_pct", 0.0))

        kpi_p1, kpi_p2, kpi_p3, kpi_p4, kpi_p5 = st.columns(5)
        kpi_p1.metric("Total Portfolio Equity", f"${tot_equity:,.2f}", f"{ret_pct:+.2f}% Overall")
        kpi_p2.metric("Available Cash Balance", f"${cash_bal:,.2f}", "Uncommitted USD")
        kpi_p3.metric("Active Deals Value", f"${open_val:,.2f}", f"{len(open_positions)} Open Deals")
        unreal_sign = "+" if unreal_pnl >= 0 else ""
        kpi_p4.metric("Unrealized MTM P&L", f"{unreal_sign}${unreal_pnl:,.2f}", "Live Mark-to-Market")
        real_sign = "+" if real_pnl >= 0 else ""
        kpi_p5.metric("Realized Closed P&L", f"{real_sign}${real_pnl:,.2f}", f"{len(closed_trades)} Trades Closed")

        # Toolbar: Refresh Quotes, Reset, Risk Sentry Audit
        t_col1, t_col2, t_col3, t_col4 = st.columns([1.5, 1.5, 2.0, 1.5])
        with t_col1:
            if st.button("🔄 Sync All Quotes & MTM", use_container_width=True, key="p_sync_btn"):
                with st.spinner("Fetching live market quotes and marking positions to market..."):
                    paper_engine.mark_to_market()
                    st.rerun()
        with t_col2:
            if st.button("🗑️ Reset Portfolio to $1M", use_container_width=True, key="p_reset_btn"):
                paper_engine.reset_portfolio()
                st.success("✅ Portfolio reset to $1,000,000.00 USD cash.")
                st.rerun()
        with t_col3:
            if st.button("🚨 Run Risk Sentry Audit", type="secondary", use_container_width=True, key="p_sentry_btn"):
                with st.spinner("Executing autonomous quantitative risk sentry audit..."):
                    from tools.risk_sentry import PortfolioRiskSentry
                    sentry = PortfolioRiskSentry(paper_engine=paper_engine)
                    sentry_res = sentry.audit_portfolio_risk()
                    st.session_state["latest_risk_audit"] = sentry_res
                    if sentry_res["total_breaches_count"] > 0:
                        st.error(f"{sentry_res['status_badge']}: {sentry_res['total_breaches_count']} active breach(es) detected!")
                    else:
                        st.success(f"{sentry_res['status_badge']}: Portfolio within nominal tail risk bounds.")
                    st.rerun()

        # Risk Sentry Surveillance Strip
        from tools.risk_sentry import PortfolioRiskSentry
        risk_sentry = PortfolioRiskSentry(paper_engine=paper_engine)
        sentry_state = risk_sentry.load_latest_sentry_state()
        s_badge = sentry_state.get("status_badge", "⚪ UNINITIALIZED")
        s_color = "#10B981" if "HEALTHY" in s_badge else ("#EF4444" if "CRITICAL" in s_badge else "#F59E0B")
        s_last = sentry_state.get("last_audited_at", "Never")
        if s_last and s_last != "Never":
            s_last = s_last[:19].replace("T", " ") + " UTC"

        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.85); border:1px solid {s_color}; border-left:4px solid {s_color}; border-radius:6px; padding:10px 14px; margin:10px 0;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <span style="font-weight:700; color:{s_color}; font-size:0.92rem;">
                    🚨 Autonomous Risk Sentry: {s_badge}
                </span>
                <span style="font-size:0.80rem; color:#94A3B8; font-family:monospace;">
                    1-Day 95% CF-VaR: <b>${sentry_state.get('var_95_cf_usd', 0.0):,.2f} USD</b> ({sentry_state.get('var_95_cf_pct', 0.0):.2f}%) | Last Audit: {s_last}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        recent_risk_alerts = risk_sentry.load_recent_risk_alerts(limit=5)
        if recent_risk_alerts:
            with st.expander(f"⚠️ Recent Risk Sentry Alerts ({len(recent_risk_alerts)})", expanded=False):
                for ra in reversed(recent_risk_alerts):
                    sev = ra.get("severity", "WARNING")
                    b_col = "#EF4444" if sev == "CRITICAL" else "#F59E0B"
                    st.markdown(f"<div style='border-left:3px solid {b_col}; padding:4px 8px; margin:4px 0; font-size:0.82rem; color:#E2E8F0;'><b>[{sev}] {ra.get('type', 'ALERT')}</b> ({ra.get('timestamp', '')[:19]}): {ra.get('message', '')}</div>", unsafe_allow_html=True)

        # Multi-Channel Webhook Alert Dispatcher Control Section
        alert_dispatcher = get_alert_dispatcher()
        channel_status = alert_dispatcher.get_channel_status()

        with st.expander("📡 Real-Time Webhook Alert Dispatcher (Discord, Slack, Telegram, REST)", expanded=False):
            st.markdown("##### 📢 Connected Notification Channels")
            ch_col1, ch_col2, ch_col3, ch_col4 = st.columns(4)
            with ch_col1:
                d_conf = channel_status["discord"]["configured"]
                d_color = "#10B981" if d_conf else "#94A3B8"
                d_label = "ACTIVE" if d_conf else "SIMULATED"
                st.markdown(f"**Discord**<br><span style='color:{d_color}; font-size:0.75rem; font-weight:700;'>● {d_label}</span>", unsafe_allow_html=True)
            with ch_col2:
                s_conf = channel_status["slack"]["configured"]
                s_color = "#10B981" if s_conf else "#94A3B8"
                s_label = "ACTIVE" if s_conf else "SIMULATED"
                st.markdown(f"**Slack**<br><span style='color:{s_color}; font-size:0.75rem; font-weight:700;'>● {s_label}</span>", unsafe_allow_html=True)
            with ch_col3:
                t_conf = channel_status["telegram"]["configured"]
                t_color = "#10B981" if t_conf else "#94A3B8"
                t_label = "ACTIVE" if t_conf else "SIMULATED"
                st.markdown(f"**Telegram**<br><span style='color:{t_color}; font-size:0.75rem; font-weight:700;'>● {t_label}</span>", unsafe_allow_html=True)
            with ch_col4:
                g_conf = channel_status["generic_rest"]["configured"]
                g_color = "#10B981" if g_conf else "#94A3B8"
                g_label = "ACTIVE" if g_conf else "SIMULATED"
                st.markdown(f"**Generic REST**<br><span style='color:{g_color}; font-size:0.75rem; font-weight:700;'>● {g_label}</span>", unsafe_allow_html=True)

            wh_b1, wh_b2 = st.columns([2.0, 3.0])
            with wh_b1:
                if st.button("🚀 Send Test Multi-Channel Webhook Alert", use_container_width=True, key="btn_test_webhook"):
                    with st.spinner("Dispatching test alert across all channels..."):
                        test_dispatch = alert_dispatcher.dispatch_risk_alert(
                            alert_type="SIMULATED_TEST_BREACH",
                            severity="CRITICAL",
                            message="Institutional Risk Sentry Test: 1-Day 95% CF-VaR simulation verification.",
                            symbol="SPY",
                            metrics={"var_95_cf_pct": 5.40, "portfolio_equity_usd": tot_equity},
                            force=True
                        )
                        st.success(f"✅ Alert Dispatched! Provenance ID: `{test_dispatch['provenance_ledger_id']}`")
                        st.rerun()

            recent_dispatches = alert_dispatcher.load_recent_dispatches(limit=5)
            if recent_dispatches:
                st.markdown("###### 📜 Recent Dispatched Webhook Payloads")
                for d in reversed(recent_dispatches):
                    sev_c = "#EF4444" if d.get("severity") == "CRITICAL" else ("#10B981" if d.get("severity") == "SUCCESS" else "#F59E0B")
                    st.markdown(
                        f"<div style='border-left:3px solid {sev_c}; background:#0B0E14; padding:6px 10px; margin:4px 0; font-size:0.78rem; font-family:monospace;'>"
                        f"<b style='color:{sev_c};'>[{d.get('severity', 'INFO')}] {d.get('event_type', 'ALERT')}</b> ({d.get('symbol', 'PORTFOLIO')}) - {d.get('payload_summary', '')}<br>"
                        f"<span style='color:#64748B;'>Timestamp: {d.get('timestamp', '')[:19]} | Ledger: <code>{d.get('provenance_ledger_id', 'N/A')}</code></span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        # ---------------------------------------------------------------------
        # BROKER GATEWAY & MULTI-EXCHANGE ORDER ROUTING CONTROL STRIP
        # ---------------------------------------------------------------------
        st.markdown("#### 🌐 Institutional Broker Gateway & Smart Order Router")
        st.caption("Switch execution gateways, select routing venues, and monitor broker connection headroom.")

        b_c1, b_c2, b_c3 = st.columns([2.0, 1.5, 1.5])
        with b_c1:
            exec_mode_options = [
                "🏢 Simulation Paper Desk ($1,000,000 Capital Anchor)",
                "🦙 Alpaca Markets Paper API (Sandbox)",
                "⚡ Alpaca Markets Live Trading (Production API)",
                "🌐 Interactive Brokers (IBKR SMART Router)"
            ]
            mode_map = {
                "🏢 Simulation Paper Desk ($1,000,000 Capital Anchor)": "SIMULATION_PAPER",
                "🦙 Alpaca Markets Paper API (Sandbox)": "ALPACA_PAPER",
                "⚡ Alpaca Markets Live Trading (Production API)": "ALPACA_LIVE",
                "🌐 Interactive Brokers (IBKR SMART Router)": "IBKR_GATEWAY"
            }
            curr_mode = router.active_mode
            default_idx = 0
            if curr_mode == "ALPACA_PAPER":
                default_idx = 1
            elif curr_mode == "ALPACA_LIVE":
                default_idx = 2
            elif curr_mode == "IBKR_GATEWAY":
                default_idx = 3

            selected_mode_label = st.selectbox(
                "Active Execution Gateway",
                exec_mode_options,
                index=default_idx,
                key="sel_exec_mode"
            )
            selected_mode = mode_map[selected_mode_label]
            if selected_mode != router.active_mode:
                router.set_execution_mode(selected_mode)
            st.session_state["active_execution_mode"] = selected_mode

        with b_c2:
            venue_options = ["SMART", "IEX (Speed Bump)", "NASDAQ", "NYSE", "CME_GLOBEX", "CBOE", "DARK_POOL_CROSS"]
            selected_venue = st.selectbox(
                "Default Routing Venue",
                venue_options,
                index=0,
                key="sel_routing_venue"
            )
            st.session_state["active_routing_venue"] = selected_venue

        with b_c3:
            # Display real-time broker connection status card
            if router.active_mode in ("ALPACA_PAPER", "ALPACA_LIVE"):
                acct = router.alpaca_client.get_account()
                status_color = "#10B981" if acct.get("status") in ("ACTIVE", "SIMULATED_ACTIVE") else "#F59E0B"
                b_status = acct.get("status", "ACTIVE")
                b_bp = acct.get("buying_power_usd", 1000000.0 * 2.0)
            elif router.active_mode == "IBKR_GATEWAY":
                acct = router.ibkr_client.get_account()
                status_color = "#38BDF8"
                b_status = acct.get("status", "STANDBY")
                b_bp = acct.get("buying_power_usd", 1000000.0 * 4.0)
            else:
                status_color = "#10B981"
                b_status = "SIMULATION_ACTIVE"
                b_bp = cash_bal * 2.0

            st.markdown(f"""
            <div style="background:#0F172A; border:1px solid #1E293B; border-radius:6px; padding:8px 12px; margin-top:24px;">
                <div style="font-size:0.75rem; color:#94A3B8;">STATUS: <b style="color:{status_color};">{b_status}</b></div>
                <div style="font-size:0.85rem; font-weight:700; color:#F8FAFC;">Buying Power: ${b_bp:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        # Active Positions Book Table
        st.markdown("#### 📋 Open Deals & Active Positions Book")
        if not open_positions:
            st.info("ℹ️ Your active portfolio is currently 100% Cash ($1,000,000.00 USD). Go to Tab 2 (Options), Tab 3 (Econometric Simulator), Tab 4 (Futures), or Tab 6 (Crypto) to execute real live deals at market prices!")
        else:
            for p in open_positions:
                p_id = p["position_id"]
                p_sym = p["symbol"]
                p_asset = p["asset_class"]
                p_side = p["side"]
                p_qty = p["quantity"]
                p_entry = p["entry_price"]
                p_curr = p.get("current_price", p_entry)
                p_cost = p["cost_basis"]
                p_val = p.get("market_value", p_cost)
                p_pnl = p.get("unrealized_pnl", 0.0)
                p_pnl_pct = p.get("unrealized_pnl_pct", 0.0)
                p_sign = "+" if p_pnl >= 0 else ""
                pnl_color = "#10B981" if p_pnl >= 0 else "#F43F5E"
                p_venue = p.get("routing_venue", "SMART")
                p_fric = p.get("tca", {}).get("total_friction_usd", 0.0)

                p_row1, p_row2, p_row3, p_row4, p_row5, p_row6 = st.columns([1.2, 1.5, 1.2, 1.5, 1.5, 1.2])
                with p_row1:
                    st.markdown(f"**{p_sym}**<br><span style='font-size:0.75rem; color:#94A3B8;'>{p_id} · {p_asset} · <span style='color:#38BDF8;'>{p_venue}</span></span>", unsafe_allow_html=True)
                with p_row2:
                    st.markdown(f"<span style='color:#38BDF8; font-weight:700;'>{p_side} {p_qty:,}</span><br><span style='font-size:0.75rem; color:#CBD5E1;'>{p.get('strategy_type', 'Standard')}</span>", unsafe_allow_html=True)
                with p_row3:
                    st.markdown(f"Entry: **${p_entry:,.2f}**<br>Live: **${p_curr:,.2f}**<br><span style='font-size:0.72rem; color:#A7F3D0;'>TCA: ${p_fric:,.2f}</span>", unsafe_allow_html=True)
                with p_row4:
                    st.markdown(f"Cost: **${p_cost:,.2f}**<br>Value: **${p_val:,.2f}**", unsafe_allow_html=True)
                with p_row5:
                    st.markdown(f"<span style='color:{pnl_color}; font-weight:800;'>{p_sign}${p_pnl:,.2f}</span><br><span style='color:{pnl_color}; font-size:0.75rem;'>{p_sign}{p_pnl_pct:.2f}%</span>", unsafe_allow_html=True)
                with p_row6:
                    if st.button("🔴 Close Deal", key=f"close_{p_id}", use_container_width=True):
                        c_ok, c_msg, c_rec = paper_engine.close_position(p_id)
                        if c_ok:
                            st.success(c_msg)
                            st.rerun()
                        else:
                            st.error(c_msg)
                st.markdown("<hr style='margin:4px 0 10px 0; border:0; border-top:1px solid #1E293B;'>", unsafe_allow_html=True)

        if closed_trades:
            with st.expander(f"📜 Closed Trades History ({len(closed_trades)} Completed Deals)", expanded=False):
                for ct in reversed(closed_trades):
                    cpnl = ct["realized_pnl"]
                    csign = "+" if cpnl >= 0 else ""
                    ccolor = "#10B981" if cpnl >= 0 else "#F43F5E"
                    st.markdown(f"""
                    <div style="background:#0F172A; border:1px solid #1E293B; border-radius:6px; padding:8px 12px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <b>{ct['symbol']}</b> ({ct['asset_class']} · {ct['strategy_type']}) · {ct['side']} {ct['quantity']} · Entry: ${ct['entry_price']:,.2f} → Exit: ${ct['exit_price']:,.2f}
                            <div style="font-size:0.75rem; color:#94A3B8;">Closed: {ct['closed_at'][:19]} · Ledger: <code>{ct.get('ledger_id', 'N/A')}</code></div>
                        </div>
                        <div style="text-align:right;">
                            <span style="color:{ccolor}; font-weight:800; font-size:1.05rem;">{csign}${cpnl:,.2f}</span>
                            <div style="color:{ccolor}; font-size:0.75rem;">{csign}{ct['realized_pnl_pct']:.2f}%</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.divider()
        st.markdown("### 🏛️ Multi-Asset Committee Review & CRO Gatekeeper Audit")
        st.caption("Coordinate execution across all 5 specialized desks, aggregate portfolio risk, and enforce independent CRO gatekeeping.")

        col_cfg1, col_cfg2 = st.columns([1.1, 2.5])
        with col_cfg1:
            st.markdown("#### 💼 Portfolio Specification")
            port_name = st.text_input("Portfolio / Mandate Name", value="Meridian Global Macro Alpha Fund", key="mo_port_name")
            total_cap = st.number_input(
                "Total Capital Allocation ($USD)",
                min_value=10_000.0,
                max_value=1_000_000_000.0,
                value=1_000_000.0,
                step=50_000.0,
                format="%.2f",
                key="mo_total_cap"
            )
            st.caption(f"💰 Selected Capital: **${total_cap:,.2f} USD**")

            preset = st.selectbox(
                "Allocation Preset",
                [
                    "Institutional Balanced (40% Eq, 30% FI, 15% Comm, 10% Crypto, 5% Opt)",
                    "Capital Preservation / Defensive (15% Eq, 65% FI, 10% Comm, 0% Crypto, 10% Opt)",
                    "Asymmetric Macro Growth (50% Eq, 10% FI, 15% Comm, 20% Crypto, 5% Opt)",
                    "Custom Allocation"
                ],
                key="mo_preset"
            )

        with col_cfg2:
            st.markdown("#### ⚖️ Asset Class Allocations ($USD)")
            if preset.startswith("Institutional Balanced"):
                eq_pct, fi_pct, comm_pct, cryp_pct, opt_pct = 40.0, 30.0, 15.0, 10.0, 5.0
            elif preset.startswith("Capital Preservation"):
                eq_pct, fi_pct, comm_pct, cryp_pct, opt_pct = 15.0, 65.0, 10.0, 0.0, 10.0
            elif preset.startswith("Asymmetric Macro Growth"):
                eq_pct, fi_pct, comm_pct, cryp_pct, opt_pct = 50.0, 10.0, 15.0, 20.0, 5.0
            else:
                eq_pct = st.slider("Equities Allocation %", 0.0, 100.0, 40.0, 1.0)
                fi_pct = st.slider("Fixed Income Allocation %", 0.0, 100.0, 30.0, 1.0)
                comm_pct = st.slider("Commodities & Futures %", 0.0, 100.0, 15.0, 1.0)
                cryp_pct = st.slider("Crypto & 24/7 Derivatives %", 0.0, 100.0, 10.0, 1.0)
                opt_pct = st.slider("Options Hedging Overlay %", 0.0, 100.0, 5.0, 1.0)

            # Convert to dollars
            allocations = {
                "equities": total_cap * (eq_pct / 100.0),
                "fixed_income": total_cap * (fi_pct / 100.0),
                "commodities": total_cap * (comm_pct / 100.0),
                "crypto": total_cap * (cryp_pct / 100.0),
                "options_overlay": total_cap * (opt_pct / 100.0)
            }

            c1, c2, c3, c4, c5 = st.columns(5)
            cards = [
                ("Equities", allocations["equities"], eq_pct, "#38BDF8"),
                ("Fixed Income", allocations["fixed_income"], fi_pct, "#10B981"),
                ("Commodities", allocations["commodities"], comm_pct, "#F59E0B"),
                ("Crypto 24/7", allocations["crypto"], cryp_pct, "#A855F7"),
                ("Options Overlay", allocations["options_overlay"], opt_pct, "#EC4899"),
            ]
            for col, (label, val, pct, border_color) in zip([c1, c2, c3, c4, c5], cards):
                with col:
                    st.markdown(f"""
                    <div style="background:#121824; border:1px solid #1E2638; border-top:3px solid {border_color}; border-radius:6px; padding:10px 6px; text-align:center; min-width:0;">
                        <div style="font-size:0.72rem; color:#94A3B8; font-weight:700; text-transform:uppercase; letter-spacing:0.03em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{label}">{label}</div>
                        <div style="font-size:1.05rem; font-weight:800; color:#F8FAFC; font-family:'JetBrains Mono',monospace; margin:4px 0; white-space:nowrap;" title="${val:,.2f}">
                            ${val:,.0f}
                        </div>
                        <div style="font-size:0.76rem; color:#10B981; font-weight:700;">
                            ↑ {pct:.1f}%
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        run_committee_btn = st.button("🚀 EXECUTE MULTI-DESK COMMITTEE AUDIT", type="primary", use_container_width=True)

        if run_committee_btn or "mo_last_result" in st.session_state:
            if run_committee_btn:
                with st.spinner("Dispatching tasks across 5 specialized desks and running CRO audit..."):
                    result = orchestrator.run_multi_asset_committee(
                        portfolio_name=port_name,
                        total_capital_usd=total_cap,
                        allocations_usd=allocations
                    )
                    st.session_state["mo_last_result"] = result
            else:
                result = st.session_state["mo_last_result"]

            st.divider()

            # Risk Verdict Banner
            verdict = result["risk_verdict"]
            v_color = "#10B981" if verdict == "APPROVED" else "#F59E0B" if verdict == "CONDITIONAL_APPROVAL" else "#F43F5E"
            v_bg = "rgba(16,185,129,0.12)" if verdict == "APPROVED" else "rgba(245,158,11,0.12)" if verdict == "CONDITIONAL_APPROVAL" else "rgba(244,63,94,0.15)"
            v_border = "#10B981" if verdict == "APPROVED" else "#F59E0B" if verdict == "CONDITIONAL_APPROVAL" else "#F43F5E"

            st.markdown(f"""
            <div style="background:{v_bg}; border:2px solid {v_border}; border-radius:8px; padding:16px 20px; margin-bottom:20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                    <div>
                        <div style="font-size:0.78rem; font-weight:700; color:{v_color}; text-transform:uppercase; letter-spacing:0.05em;">
                            CROSS-ASSET RISK OFFICER COMMITTEE VERDICT
                        </div>
                        <div style="font-size:1.6rem; font-weight:900; color:#F8FAFC; margin-top:2px;">
                            {verdict.replace('_', ' ')}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-family:monospace; font-size:0.85rem; color:#94A3B8;">PROVENANCE: {result['master_ledger_id']}</span>
                    </div>
                </div>
                <div style="font-size:0.92rem; color:#CBD5E1; margin-top:8px;">
                    {result['verdict_rationale']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Executive KPI Cards
            vm = result["var_metrics"]
            kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
            kpi1.metric("1-Day 99% VaR ($)", f"${vm.get('var_99_dollar', 0):,.0f}", f"-{vm.get('var_99_pct', 0):.2f}%")
            kpi2.metric("1-Day 99% CVaR ($)", f"${vm.get('cvar_99_dollar', 0):,.0f}", f"-{vm.get('cvar_99_pct', 0):.2f}%")
            kpi3.metric("Annualized Volatility", f"{vm.get('annualized_vol_pct', 0):.2f}%", "Normal Vol")
            kpi4.metric("Total Red Flags", str(result["total_red_flags"]), f"{result['critical_flags_count']} Critical")
            kpi5.metric("Master Ledger Signature", result["master_ledger_id"], "HMAC-SHA256")

            # Desk Synthesis Cards
            st.markdown("#### 📋 Specialized Desk Reports & Findings")
            d_cols = st.columns(5)
            desk_data = [
                ("Options Greek Strategist", "#818CF8", result["desk_reports"].get("Options Greek Strategist", {})),
                ("Futures & Commodity Desk", "#F59E0B", result["desk_reports"].get("Futures & Commodity Desk", {})),
                ("Fixed Income Macro", "#10B981", result["desk_reports"].get("Fixed Income Macro Agent", {})),
                ("Crypto & 24/7 Derivatives", "#38BDF8", result["desk_reports"].get("Crypto & 24/7 Derivatives Agent", {})),
                ("Cross-Asset Risk Officer", "#F43F5E", result["desk_reports"].get("Cross-Asset Risk Officer", {}))
            ]

            for i, (name, color, d_res) in enumerate(desk_data):
                with d_cols[i]:
                    st.markdown(f"""
                    <div style="background:rgba(18,24,36,0.85); border:1px solid #1E2638; border-top:3px solid {color}; border-radius:6px; padding:12px; height:180px; display:flex; flex-direction:column; justify-content:space-between;">
                        <div>
                            <div style="font-weight:700; font-size:0.85rem; color:#F8FAFC;">{name}</div>
                            <div style="font-size:0.75rem; color:#94A3B8; margin-top:6px;">
                                Provenance: <code>{d_res.get('provenance_ledger_id', 'N/A')}</code>
                            </div>
                            <div style="font-size:0.75rem; color:#CBD5E1; margin-top:8px;">
                                Red Flags: <b>{len(d_res.get('red_flags', []))}</b> detected
                            </div>
                        </div>
                        <div style="font-size:0.70rem; color:{color}; font-weight:600; text-transform:uppercase;">
                            AUDITED DESK DELIVERABLE
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Master Red Flags Register
            st.divider()
            st.markdown("#### 🚨 Master Institutional Red Flags Register")
            st.caption("Consolidated risk warnings from all 5 desks with severity classification and operational impact.")

            flags_register = result.get("red_flags_register", [])
            if not flags_register:
                st.success("✅ Zero red flags detected across all 5 specialized desks.")
            else:
                for rf in flags_register:
                    sev = rf.get("severity", "MEDIUM")
                    badge_color = "#F43F5E" if sev == "CRITICAL" else "#F59E0B" if sev == "HIGH" else "#38BDF8"
                    st.markdown(f"""
                    <div style="background:rgba(18,24,36,0.6); border:1px solid #1E2638; border-left:4px solid {badge_color}; border-radius:6px; padding:10px 14px; margin-bottom:8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:700; color:#F8FAFC; font-size:0.88rem;">{rf.get('category', 'Risk Notice')}</span>
                            <span style="background:rgba(255,255,255,0.08); color:{badge_color}; font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:4px;">
                                {sev} · {rf.get('source_desk', 'Desk')}
                            </span>
                        </div>
                        <div style="font-size:0.82rem; color:#94A3B8; margin-top:4px;">
                            {rf.get('message', '')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Download & Export Dossier
            st.divider()
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    label="💾 Download Institutional Memorandum (JSON)",
                    data=json.dumps(result, indent=2, default=str),
                    file_name=f"meridian_memorandum_{datetime.date.today().isoformat()}.json",
                    mime="application/json",
                    use_container_width=True
                )
            with col_dl2:
                # Format trade ticket CSV
                trade_ticket_csv = "Asset_Class,Allocation_USD,Weight_Pct,Assigned_Desk,Risk_Status\n"
                for ac, usd in allocations.items():
                    pct = (usd / total_cap) * 100.0
                    trade_ticket_csv += f"{ac},{usd:.2f},{pct:.2f}%,Multi-Desk,{verdict}\n"
                st.download_button(
                    label="📊 Download Multi-Asset Trade Tickets (CSV)",
                    data=trade_ticket_csv,
                    file_name=f"meridian_trade_tickets_{datetime.date.today().isoformat()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

    # =========================================================================
    # TAB 2: OPTIONS GREEK STRATEGIST
    # =========================================================================
    with tab_opt:
        st.markdown("### 🎯 Options Greek Strategist")
        st.caption("Analytical Black-Scholes-Merton option pricing, 1st/2nd-order Greeks, and multi-leg strategy payoff distributions.")

        with st.expander("📐 Black-Scholes-Merton Analytical Formulas & Greeks Audit", expanded=False):
            st.markdown(r"""
            #### 🧮 Black-Scholes-Merton Options Pricing & Greek Sensitivities
            - **Standard Normal Parameters**:
              $$d_1 = \frac{\ln(S / K) + \left(r - q + \frac{1}{2}\sigma^2\right)\tau}{\sigma \sqrt{\tau}}, \quad d_2 = d_1 - \sigma \sqrt{\tau}$$
            - **Option Pricing Equations**:
              $$C(S, K, \tau) = S e^{-q\tau} N(d_1) - K e^{-r\tau} N(d_2)$$
              $$P(S, K, \tau) = K e^{-r\tau} N(-d_2) - S e^{-q\tau} N(-d_1)$$
            - **First-Order Greeks**:
              $$\text{Delta } (\Delta): \quad \Delta_{\text{call}} = e^{-q\tau} N(d_1), \quad \Delta_{\text{put}} = -e^{-q\tau} N(-d_1)$$
              $$\text{Vega } (\nu): \quad \nu = \frac{S e^{-q\tau} \sqrt{\tau} N'(d_1)}{100} \quad \left(\frac{\partial V}{\partial \sigma} \text{ per 1\% move}\right)$$
              $$\text{Daily Theta } (\Theta): \quad \Theta_{\text{daily}} = \frac{1}{365} \left[ -\frac{S e^{-q\tau} N'(d_1) \sigma}{2\sqrt{\tau}} - r K e^{-r\tau} N(d_2) + q S e^{-q\tau} N(d_1) \right]$$
              $$\text{Rho } (\rho): \quad \rho_{\text{call}} = K \tau e^{-r\tau} N(d_2) \times 0.01, \quad \rho_{\text{put}} = -K \tau e^{-r\tau} N(-d_2) \times 0.01$$
            - **Second-Order Greeks**:
              $$\text{Gamma } (\Gamma): \quad \Gamma = \frac{e^{-q\tau} N'(d_1)}{S \sigma \sqrt{\tau}} = \frac{\partial^2 V}{\partial S^2}$$
              $$\text{Vanna}: \quad \text{Vanna} = -e^{-q\tau} N'(d_1) \frac{d_2}{\sigma} = \frac{\partial \Delta}{\partial \sigma}$$
              $$\text{Volga}: \quad \text{Volga} = S e^{-q\tau} N'(d_1) \sqrt{\tau} \frac{d_1 d_2}{100 \sigma} = \frac{\partial \nu}{\partial \sigma}$$
            - **Put-Call Parity**:
              $$C - P = S e^{-q\tau} - K e^{-r\tau}$$
            """)

        col_opt_mode1, col_opt_mode2 = st.columns([1, 2])
        with col_opt_mode1:
            st.markdown("#### ⚙️ Single Contract Evaluator")
            col_search_in, col_search_btn = st.columns([2.5, 1])
            with col_search_in:
                opt_query = st.text_input(
                    "Company Name or Ticker",
                    value=st.session_state.get("opt_query_val", "MU"),
                    key="opt_tk_query",
                    help="Type company name (e.g. micron, apple, nvidia, tesla) or ticker (e.g. MU, AAPL, NVDA)"
                )
            with col_search_btn:
                st.write("")
                st.write("")
                opt_sync = st.button("🔄 Sync Live", key="opt_sync_quote_btn", use_container_width=True)

            # Quick Pills
            st.caption("Quick Select: ")
            q_cols = st.columns(4)
            for i, (q_label, q_sym) in enumerate([("MU", "MU"), ("NVDA", "NVDA"), ("AAPL", "AAPL"), ("TSLA", "TSLA")]):
                if q_cols[i].button(q_label, key=f"qpill_opt_{q_sym}", use_container_width=True):
                    opt_query = q_sym
                    st.session_state["opt_query_val"] = q_sym
                    st.rerun()

            # Resolve live market data
            live_asset = resolve_and_fetch_live_asset(opt_query)
            st.session_state["opt_query_val"] = live_asset["symbol"]

            # Live Market Banner
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.12); border:1px solid #10B981; border-radius:6px; padding:10px 14px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:800; color:#F8FAFC; font-size:0.90rem;">
                        🟢 {live_asset['name']} ({live_asset['exchange']}: {live_asset['symbol']})
                    </span>
                    <span style="font-family:monospace; font-weight:800; color:#10B981; font-size:1.02rem;">
                        ${live_asset['price']:,.2f} USD
                    </span>
                </div>
                <div style="font-size:0.75rem; color:#CBD5E1; margin-top:4px;">
                    🎯 ATM Strike: <b>${live_asset['atm_strike']:,.2f}</b> · 📊 Live IV: <b>{live_asset['atm_iv_pct']:.1f}%</b> · ⏳ Expiry: <b>{live_asset['selected_expiry'] or 'Active'} ({live_asset['dte']}d)</b> · 🔄 PCR: <b>{live_asset['pcr_oi']:.2f}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

            opt_spot = st.number_input(
                "Spot Price ($)",
                min_value=0.1,
                value=float(live_asset["price"]),
                step=1.0,
                format="%.2f",
                key=f"opt_sp_{live_asset['symbol']}"
            )
            opt_strike = st.number_input(
                "Strike Price ($)",
                min_value=0.1,
                value=float(live_asset["atm_strike"]),
                step=1.0,
                format="%.2f",
                key=f"opt_sk_{live_asset['symbol']}"
            )
            opt_dte = st.number_input(
                "Days to Expiration (DTE)",
                min_value=1,
                value=int(live_asset["dte"]),
                step=1,
                key=f"opt_dt_{live_asset['symbol']}"
            )
            opt_vol_pct = st.number_input(
                "Implied Volatility (%)",
                min_value=1.0,
                max_value=300.0,
                value=float(live_asset["atm_iv_pct"]),
                step=0.5,
                format="%.1f",
                key=f"opt_vl_{live_asset['symbol']}"
            )
            opt_r_pct = st.number_input("Risk-Free Rate (%)", min_value=0.0, max_value=20.0, value=4.5, step=0.1, key="opt_rf")
            opt_type = st.radio("Option Type", ["Call", "Put"], horizontal=True, key="opt_tp")

            expiry_years = opt_dte / 365.0
            vol_decimal = opt_vol_pct / 100.0
            r_decimal = opt_r_pct / 100.0

            opt_res = orchestrator.options_desk.analyze_contract(
                underlying_ticker=live_asset["symbol"],
                spot_price=opt_spot,
                strike_price=opt_strike,
                time_to_expiry_years=expiry_years,
                volatility=vol_decimal,
                risk_free_rate=r_decimal,
                option_type=opt_type.lower()
            )

        with col_opt_mode2:
            st.markdown("#### 📊 Analytical Greeks & Sensitivities")
            g = opt_res["greeks"]
            c_g1, c_g2, c_g3, c_g4 = st.columns(4)
            c_g1.metric("Fair Value", f"${g['price']:,.2f}", f"Intrinsic: ${g['intrinsic_value']:,.2f}")
            c_g2.metric("Delta (Δ)", f"{g['delta']:+.4f}", f"{opt_res['hedging_delta_shares_per_contract']:,} shares")
            c_g3.metric("Gamma (Γ)", f"{g['gamma']:.6f}", "dΔ / dSpot")
            c_g4.metric("Vega (ν)", f"${g['vega']:,.2f}", "per 1% Vol")

            c_g5, c_g6, c_g7, c_g8 = st.columns(4)
            c_g5.metric("Daily Theta (Θ)", f"${g['theta_daily']:,.3f}/day", f"${g['theta_annual']:,.2f}/yr")
            c_g6.metric("Rho (ρ)", f"${g['rho']:,.3f}", "per 1% Rate")
            c_g7.metric("Vanna", f"{g['vanna']:.6f}", "dΔ / dVol")
            c_g8.metric("Volga", f"{g['volga']:.6f}", "dVega / dVol")

            st.markdown("#### 📈 Multi-Leg Strategy Payoff Simulator")
            strat_choice = st.selectbox(
                "Select Strategy Template",
                ["Long Straddle", "Bull Call Spread", "Iron Condor", "Protective Collar", "Covered Call"],
                key="opt_strat_choice"
            )

            # Build legs dynamically
            if strat_choice == "Long Straddle":
                legs = [
                    {"type": "call", "strike": opt_spot, "quantity": 1, "volatility": vol_decimal, "expiry_years": expiry_years},
                    {"type": "put", "strike": opt_spot, "quantity": 1, "volatility": vol_decimal, "expiry_years": expiry_years}
                ]
            elif strat_choice == "Bull Call Spread":
                legs = [
                    {"type": "call", "strike": opt_spot * 0.98, "quantity": 1, "volatility": vol_decimal, "expiry_years": expiry_years},
                    {"type": "call", "strike": opt_spot * 1.05, "quantity": -1, "volatility": vol_decimal, "expiry_years": expiry_years}
                ]
            elif strat_choice == "Iron Condor":
                legs = [
                    {"type": "put", "strike": opt_spot * 0.90, "quantity": 1, "volatility": vol_decimal, "expiry_years": expiry_years},
                    {"type": "put", "strike": opt_spot * 0.95, "quantity": -1, "volatility": vol_decimal, "expiry_years": expiry_years},
                    {"type": "call", "strike": opt_spot * 1.05, "quantity": -1, "volatility": vol_decimal, "expiry_years": expiry_years},
                    {"type": "call", "strike": opt_spot * 1.10, "quantity": 1, "volatility": vol_decimal, "expiry_years": expiry_years}
                ]
            elif strat_choice == "Protective Collar":
                legs = [
                    {"type": "stock", "quantity": 100},
                    {"type": "put", "strike": opt_spot * 0.95, "quantity": 1, "volatility": vol_decimal, "expiry_years": expiry_years},
                    {"type": "call", "strike": opt_spot * 1.08, "quantity": -1, "volatility": vol_decimal, "expiry_years": expiry_years}
                ]
            else:  # Covered Call
                legs = [
                    {"type": "stock", "quantity": 100},
                    {"type": "call", "strike": opt_spot * 1.05, "quantity": -1, "volatility": vol_decimal, "expiry_years": expiry_years}
                ]

            strat_res = orchestrator.options_desk.evaluate_strategy(
                strategy_name=strat_choice,
                underlying_ticker=live_asset["symbol"],
                spot_price=opt_spot,
                legs=legs
            )

            sa = strat_res["strategy_analysis"]
            pnl_c = sa["pnl_curve"]

            fig_pnl = go.Figure()
            fig_pnl.add_trace(go.Scatter(
                x=pnl_c["spots"], y=pnl_c["pnls"],
                mode="lines", name=f"{strat_choice} PnL",
                line=dict(color="#10B981", width=3)
            ))
            fig_pnl.add_hline(y=0, line_dash="dash", line_color="#64748B")
            fig_pnl.add_vline(
                x=opt_spot,
                line_dash="dot",
                line_color="#38BDF8",
                annotation_text=f" Spot ${opt_spot:,.2f} ",
                annotation_position="top left",
                annotation_font=dict(color="#38BDF8", size=10.5, family="monospace"),
                annotation_bgcolor="rgba(15, 23, 42, 0.92)",
                annotation_bordercolor="#38BDF8",
                annotation_borderwidth=1
            )
            fig_pnl.update_layout(
                title=dict(
                    text=f"<b>{strat_choice}</b> Payoff at Expiration ({live_asset['symbol']})",
                    x=0.01,
                    y=0.98,
                    xanchor="left",
                    yanchor="top",
                    font=dict(size=13, color="#F8FAFC")
                ),
                xaxis_title="Underlying Spot Price ($)",
                yaxis_title="Net PnL ($)",
                template="plotly_dark",
                height=360,
                margin=dict(l=35, r=35, t=65, b=25)
            )
            st.plotly_chart(fig_pnl, use_container_width=True)

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Structure", sa["structure"], f"${sa['net_debit_credit']:,.2f}")
            sc2.metric("Net Delta", f"{sa['net_delta']:+.3f}", "Directional bias")
            sc3.metric("Net Vega", f"${sa['net_vega']:,.2f}", "per 1% Vol")
            sc4.metric("Net Daily Theta", f"${sa['net_theta_daily']:,.2f}/day", "Time carry")

            # Quick econometric probability metrics
            prob_sim_quick = EconometricProbabilitySimulator()
            quick_prob = prob_sim_quick.simulate_options_strategy_probability(
                spot=opt_spot,
                legs=legs,
                risk_free_rate=r_decimal,
                target_days=max(1, opt_dte // 2),
                iv_shift_pct=0.0
            )
            qp = quick_prob["probability_metrics"]
            sp1, sp2, sp3, sp4 = st.columns(4)
            sp1.metric("Prob of Profit (POP)", f"{qp['probability_of_profit_pct']:.1f}%", f"Fat-tail: {qp['econometric_adjusted_pop_pct']:.1f}%")
            sp2.metric("Expected Value (EV)", f"${qp['expected_value_usd']:+,.2f}", "Statistical EV")
            sp3.metric("Max Profit / Loss", f"${qp['max_profit_usd']:+,.2f}", f"Max loss: ${qp['max_loss_usd']:,.2f}")
            sp4.metric("Half-Kelly Allocation", f"{qp['kelly_fraction_half_pct']:.1f}%", f"Win/Loss: {qp['win_loss_ratio']:.2f}x")

            # -----------------------------------------------------------------
            # LIVE DEAL EXECUTION DESK ($1,000,000 SIMULATION CAPITAL)
            # -----------------------------------------------------------------
            st.divider()
            st.markdown("#### ⚡ Live Deal Execution Desk ($1,000,000 Simulation Capital)")
            st.caption("Place real-market paper orders executed against live quotes and debited directly from your $1,000,000 portfolio cash.")

            pe = get_paper_trading_engine()
            p_state = pe.load_portfolio()
            p_cash = float(p_state.get("cash_balance", INITIAL_PORTFOLIO_CASH))

            c_ex1, c_ex2, c_ex3 = st.columns([1.2, 1, 1.3])
            with c_ex1:
                deal_structure = st.radio(
                    "Deal Instrument",
                    [
                        f"Single Option ({opt_type} @ ${opt_strike:,.2f})",
                        f"Multi-Leg Strategy ({strat_choice})",
                        f"Underlying Equity ({live_asset['symbol']} Shares)"
                    ],
                    key=f"opt_deal_struct_{live_asset['symbol']}"
                )
            with c_ex2:
                deal_action = st.radio("Order Side", ["BUY (Long)", "SELL (Short)"], horizontal=True, key=f"opt_deal_side_{live_asset['symbol']}")
                deal_qty = st.number_input("Order Quantity", min_value=1, max_value=1000, value=1, step=1, key=f"opt_deal_qty_{live_asset['symbol']}")

            with c_ex3:
                clean_side = "BUY" if "BUY" in deal_action else "SELL"
                if "Single Option" in deal_structure:
                    unit_px = g["price"]
                    total_deal_cost = deal_qty * unit_px * 100.0
                    deal_asset_class = "Options"
                    deal_strat_name = f"Long {opt_type}" if clean_side == "BUY" else f"Short {opt_type}"
                    deal_mult = 100.0
                elif "Multi-Leg" in deal_structure:
                    unit_px = abs(strat_res["strategy_analysis"]["net_debit_credit"])
                    total_deal_cost = deal_qty * unit_px * 100.0
                    deal_asset_class = "Options"
                    deal_strat_name = strat_choice
                    deal_mult = 100.0
                else:
                    unit_px = opt_spot
                    total_deal_cost = deal_qty * unit_px
                    deal_asset_class = "Equities"
                    deal_strat_name = "Long Equity" if clean_side == "BUY" else "Short Equity"
                    deal_mult = 1.0

                active_venue = st.session_state.get("active_routing_venue", "SMART")
                active_mode = st.session_state.get("active_execution_mode", "SIMULATION_PAPER")
                tca_deal = ExecutionCostModel.calculate_execution_costs(
                    asset_class=deal_asset_class,
                    side=clean_side,
                    quantity=float(deal_qty),
                    price=float(unit_px)
                )

                st.markdown(f"""
                <div style="background:#0F172A; border:1px solid #1E293B; border-radius:6px; padding:10px 14px; margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:0.75rem; color:#94A3B8; text-transform:uppercase;">Outlay · Venue: <b style="color:#38BDF8;">{active_venue}</b></span>
                        <span style="font-size:1.1rem; font-weight:800; color:#F8FAFC;">${total_deal_cost:,.2f} USD</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; color:#38BDF8; margin-top:2px;">
                        <span>Available Cash: <b>${p_cash:,.2f} USD</b></span>
                        <span style="color:#A7F3D0;">Est TCA Friction: <b>${tca_deal['total_friction_usd']:,.2f} USD</b> ({tca_deal['friction_basis_points']:.1f} bps)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("🟢 EXECUTE REAL DEAL AT MARKET ($)", type="primary", use_container_width=True, key=f"btn_exec_deal_{live_asset['symbol']}"):
                    exec_ok, exec_msg, exec_pos = pe.execute_trade(
                        symbol=live_asset["symbol"],
                        asset_class=deal_asset_class,
                        side=clean_side,
                        quantity=float(deal_qty),
                        price=float(unit_px),
                        strategy_type=deal_strat_name,
                        multiplier=deal_mult,
                        routing_venue=active_venue,
                        execution_mode=active_mode,
                        notes=f"Executed via Options Greek Desk for {live_asset['name']}"
                    )
                    if exec_ok:
                        st.success(exec_msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(exec_msg)

    # =========================================================================
    # TAB 3: ECONOMETRIC PROBABILITY SIMULATOR
    # =========================================================================
    with tab_prob:
        st.markdown("### 🎲 Econometric Probability Simulator")
        st.caption("Cross-asset continuous probability density modeling, dynamic Target Date P&L sliders, IV shifts, standard deviation cones (±1σ, ±2σ, ±3σ), and Cornish-Fisher fat-tail adjustments.")

        with st.expander("📐 Econometric Probability Methods, Barrier Hitting Times & Quantitative Rules Audit", expanded=False):
            st.markdown(r"""
            #### 🧮 Econometric Probability Theory & Interactive Strategy Mathematics
            - **Continuous Risk-Neutral Lognormal Density Function**:
              $$f(S_T) = \frac{1}{S_T \sigma \sqrt{2\pi T}} \exp\left( -\frac{\left(\ln(S_T / S_0) - (\mu - \frac{1}{2}\sigma^2)T\right)^2}{2\sigma^2 T} \right)$$
            - **Probability of Profit (POP %)**:
              $$\text{POP} = \int_{S_T: \text{PnL}(S_T) > 0} f(S_T) \, dS_T$$
            - **Target Date P&L Equation (Interim Horizon)**:
              At target time $t \in [0, T]$ with implied volatility shock $\Delta\sigma$:
              $$\text{PnL}_{\text{target}}(S_t) = \sum_{i=1}^M q_i \cdot \text{BSM}\left(S_t, K_i, T - t, r, \sigma_i + \Delta\sigma, \text{type}_i\right) - \text{Initial Cost}$$
            - **Continuous Barrier Touch Probability (First Hitting Time / Reflection Principle)**:
              For underlying spot $S_0$ and barrier price $B$ over horizon $T$ with drift $\alpha = \mu - \frac{1}{2}\sigma^2$:
              $$P(\tau_B \le T) = N\left(\frac{-\ln(B/S_0) + \alpha T}{\sigma\sqrt{T}}\right) + \left(\frac{B}{S_0}\right)^{\frac{2\alpha}{\sigma^2}} N\left(\frac{-\ln(B/S_0) - \alpha T}{\sigma\sqrt{T}}\right)$$
              Touch probability is significantly higher than expiration finish probability ($P_{\text{touch}} \approx 2 \times P_{\text{finish}}$ for ATM).
            - **Cornish-Fisher Fat-Tail (Leptokurtosis & Skewness) Expansion**:
              Adjusts standard Gaussian quantile $z_\alpha$ for empirical asset return asymmetry:
              $$z_{\text{CF}} = z + \frac{S}{6}(z^2 - 1) + \frac{K}{24}(z^3 - 3z) - \frac{S^2}{36}(2z^3 - 5z)$$
              Where $S$ is sample skewness ($S < 0$ in market panics) and $K$ is excess kurtosis ($K > 0$ for fat tails).
            - **Standard Deviation Cones**:
              $$\pm 1\sigma \text{ (68.27\%)} = S_0 \exp\left( (\mu - \frac{1}{2}\sigma^2)T \pm 1.0 \sigma \sqrt{T} \right)$$
              $$\pm 2\sigma \text{ (95.45\%)} = S_0 \exp\left( (\mu - \frac{1}{2}\sigma^2)T \pm 2.0 \sigma \sqrt{T} \right)$$
              $$\pm 3\sigma \text{ (99.73\%)} = S_0 \exp\left( (\mu - \frac{1}{2}\sigma^2)T \pm 3.0 \sigma \sqrt{T} \right)$$
            - **Statistical Expected Value (EV)**:
              $$\mathbb{E}[\text{PnL}] = \int_{-\infty}^{\infty} \text{PnL}(S_T) f(S_T) \, dS_T$$
            - **Half-Kelly Capital Allocation Rule**:
              $$f^* = \frac{1}{2} \left[ \frac{p \cdot b - (1 - p)}{b} \right] \quad \text{where } p = \text{POP}, \; b = \frac{\text{Avg Win}}{\text{Avg Loss}}$$
            """)

        sim_asset_mode = st.radio(
            "Select Probability Simulation Domain",
            [
                "🎯 Options Multi-Leg Strategy (Interactive Mode)",
                "📈 Equities & Single Stocks (Target vs Stop-Loss Touch Risk)",
                "🌾 Futures & Commodities (Roll Horizon & Margin Call Probability)",
                "⚡ Crypto 24/7 Perpetuals (Liquidation Breach Probability)",
                "🛡️ Multi-Asset Portfolio (Max Drawdown & Hurdle Probability)"
            ],
            horizontal=True,
            key="sim_asset_mode"
        )

        sim_engine = EconometricProbabilitySimulator()

        # ---------------------------------------------------------------------
        # 1. OPTIONS MULTI-LEG STRATEGY (INTERACTIVE MODE)
        # ---------------------------------------------------------------------
        if "Options" in sim_asset_mode:
            col_sb1, col_sb2 = st.columns([1.1, 1.9])
            with col_sb1:
                st.markdown("#### ⚙️ Strategy Specification")
                sb_col_in, sb_col_btn = st.columns([2.5, 1])
                with sb_col_in:
                    sb_query = st.text_input(
                        "Company Name or Symbol",
                        value=st.session_state.get("sb_query_val", "MU"),
                        key="sb_tk_query",
                        help="Type company name (e.g. micron, apple, nvidia, tesla) or ticker (e.g. MU, AAPL, NVDA)"
                    )
                with sb_col_btn:
                    st.write("")
                    st.write("")
                    sb_sync = st.button("🔄 Sync", key="sb_sync_btn", use_container_width=True)

                sb_live = resolve_and_fetch_live_asset(sb_query)
                st.session_state["sb_query_val"] = sb_live["symbol"]

                st.markdown(f"""
                <div style="background:rgba(16,185,129,0.12); border:1px solid #10B981; border-radius:6px; padding:8px 12px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:800; color:#F8FAFC; font-size:0.86rem;">
                            🟢 {sb_live['name']} ({sb_live['symbol']})
                        </span>
                        <span style="font-family:monospace; font-weight:800; color:#10B981; font-size:0.95rem;">
                            ${sb_live['price']:,.2f} USD
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                sb_strat = st.selectbox(
                    "Strategy Structure",
                    ["Bull Call Spread", "Bear Put Spread", "Long Straddle", "Iron Condor", "Covered Call", "Short Put"],
                    key="sb_strat_select"
                )
                sb_spot = st.number_input("Underlying Spot ($)", min_value=0.1, value=float(sb_live["price"]), step=1.0, format="%.2f", key=f"sb_sp_{sb_live['symbol']}")
                sb_dte = st.number_input("Days to Expiration (DTE)", min_value=2, value=max(2, int(sb_live["dte"])), step=1, key=f"sb_dte_{sb_live['symbol']}")
                sb_iv = st.number_input("Implied Volatility (%)", min_value=1.0, max_value=300.0, value=float(sb_live["atm_iv_pct"]), step=0.5, format="%.1f", key=f"sb_iv_{sb_live['symbol']}")
                sb_rf = st.number_input("Risk-Free Rate (%)", min_value=0.0, max_value=20.0, value=4.5, step=0.1, key="sb_rf")

                sb_moments = get_cached_empirical_moments(sb_live["symbol"])

                sb_calib_mode = st.radio(
                    "Econometric Calibration Engine",
                    [
                        "📡 Auto-Calibrated (252d Live Return Moments)",
                        "🎛️ Interactive Custom Scenario (Manual Sliders)"
                    ],
                    horizontal=True,
                    key=f"sb_calib_mode_{sb_live['symbol']}"
                )

                if sb_calib_mode.startswith("📡"):
                    sb_skew = float(sb_moments["sample_skewness"])
                    sb_kurt = float(sb_moments["sample_excess_kurtosis"])
                    sb_drift = float(sb_moments["annualized_drift"])
                    st.markdown(f"""
                    <div style="background:rgba(168,85,247,0.10); border:1px solid #A855F7; border-radius:6px; padding:8px 12px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:700; color:#F8FAFC; font-size:0.82rem;">
                                🔬 252d Return Moments ({sb_moments['tail_regime'][:24]}):
                            </span>
                            <span style="font-family:monospace; font-weight:700; color:#A855F7; font-size:0.82rem;">
                                Skew: {sb_skew:+.2f} | Kurt: {sb_kurt:+.2f} | Drift: {sb_moments['annualized_drift_pct']:+.1f}%
                            </span>
                        </div>
                        <div style="font-size:0.75rem; color:#94A3B8; margin-top:3px;">
                            Jarque-Bera: <b>{sb_moments['jarque_bera_stat']:,.1f}</b> (p={sb_moments['jarque_bera_p_value']:.4f}) — <b>{'Normality REJECTED' if sb_moments['normality_rejected'] else 'Normal Accepted'}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.caption("🎛️ Interactive sliders directly warp the probability curves and metrics in real time:")
                    c_sk1, c_sk2 = st.columns(2)
                    with c_sk1:
                        sb_skew = st.slider("Sample Skewness (S)", -2.50, 1.50, float(sb_moments["sample_skewness"]), 0.05, key=f"sb_skew_sl_{sb_live['symbol']}", help="Negative = crash/downside tail elongation, Positive = upside explosion")
                        sb_drift_pct = st.slider("Annualized Drift (μ %)", -50.0, 50.0, float(sb_moments["annualized_drift_pct"]), 0.5, key=f"sb_drift_sl_{sb_live['symbol']}")
                    with c_sk2:
                        sb_kurt = st.slider("Excess Kurtosis (K)", 0.0, 10.0, max(0.0, float(sb_moments["sample_excess_kurtosis"])), 0.10, key=f"sb_kurt_sl_{sb_live['symbol']}", help="K > 0 = Leptokurtic fat tails, higher black swan probability")
                        sb_rf = st.number_input("Risk-Free Rate (%)", min_value=0.0, max_value=20.0, value=float(sb_rf), step=0.1, key=f"sb_rf_in_{sb_live['symbol']}")
                    sb_drift = sb_drift_pct / 100.0

                st.markdown("#### 🎛️ Dynamic Target Date & IV Sliders")
                sb_target_day = st.slider("Target Date (Days from Today)", 0, int(sb_dte), int(sb_dte // 2), key=f"sb_td_slider_{sb_live['symbol']}")
                sb_iv_shift = st.slider("Implied Volatility Shift (%)", -40.0, 40.0, 0.0, 1.0, key=f"sb_iv_slider_{sb_live['symbol']}")
                sb_target_spot = st.number_input("Target Evaluation Spot ($)", value=float(sb_spot), step=1.0, key=f"sb_tsp_{sb_live['symbol']}")
                sb_use_sabr = st.checkbox(
                    "Apply Parametric SABR Smile Surface",
                    value=True,
                    help="Interpolate exact out-of-the-money strike implied volatilities from calibrated SABR model instead of flat ATM IV.",
                    key=f"sb_sabr_chk_{sb_live['symbol']}"
                )

                sb_expiry_yr = sb_dte / 365.0
                sb_vol_dec = sb_iv / 100.0
                sb_r_dec = sb_rf / 100.0

                # Build Strategy Legs
                if sb_strat == "Bull Call Spread":
                    sb_legs = [
                        {"type": "call", "strike": sb_spot * 0.98, "quantity": 1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr},
                        {"type": "call", "strike": sb_spot * 1.05, "quantity": -1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr}
                    ]
                elif sb_strat == "Bear Put Spread":
                    sb_legs = [
                        {"type": "put", "strike": sb_spot * 1.02, "quantity": 1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr},
                        {"type": "put", "strike": sb_spot * 0.95, "quantity": -1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr}
                    ]
                elif sb_strat == "Long Straddle":
                    sb_legs = [
                        {"type": "call", "strike": sb_spot, "quantity": 1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr},
                        {"type": "put", "strike": sb_spot, "quantity": 1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr}
                    ]
                elif sb_strat == "Iron Condor":
                    sb_legs = [
                        {"type": "put", "strike": sb_spot * 0.90, "quantity": 1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr},
                        {"type": "put", "strike": sb_spot * 0.95, "quantity": -1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr},
                        {"type": "call", "strike": sb_spot * 1.05, "quantity": -1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr},
                        {"type": "call", "strike": sb_spot * 1.10, "quantity": 1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr}
                    ]
                elif sb_strat == "Covered Call":
                    sb_legs = [
                        {"type": "stock", "quantity": 100},
                        {"type": "call", "strike": sb_spot * 1.05, "quantity": -1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr}
                    ]
                else:  # Short Put
                    sb_legs = [
                        {"type": "put", "strike": sb_spot * 0.95, "quantity": -1, "volatility": sb_vol_dec, "expiry_years": sb_expiry_yr}
                    ]

                sb_sim_res = sim_engine.simulate_options_strategy_probability(
                    spot=sb_spot,
                    legs=sb_legs,
                    risk_free_rate=sb_r_dec,
                    custom_drift=sb_drift,
                    skewness=sb_skew,
                    kurtosis=sb_kurt,
                    target_days=sb_target_day,
                    iv_shift_pct=sb_iv_shift,
                    apply_sabr_smile=sb_use_sabr
                )

            with col_sb2:
                st.markdown("#### 📊 Strategy Payoff & Probability Density Curves")
                tda = sb_sim_res["target_date_analysis"]
                pm = sb_sim_res["probability_metrics"]
                econo = sb_sim_res["econometric_metrics"]

                fig_sb = make_subplots(specs=[[{"secondary_y": True}]])

                # Trace 1: PnL at Expiry
                fig_sb.add_trace(
                    go.Scatter(
                        x=tda["spot_grid"],
                        y=tda["expiry_pnl_curve"],
                        mode="lines",
                        name="PnL at Expiry",
                        line=dict(color="#10B981", width=3)
                    ),
                    secondary_y=False
                )

                # Trace 2: PnL on Target Date
                fig_sb.add_trace(
                    go.Scatter(
                        x=tda["spot_grid"],
                        y=tda["target_pnl_curve"],
                        mode="lines",
                        name=f"PnL Day {sb_target_day} (IV {sb_iv_shift:+.0f}%)",
                        line=dict(color="#38BDF8", width=2.5, dash="dash")
                    ),
                    secondary_y=False
                )

                # Trace 3: Empirical Cornish-Fisher PDF (Fat Tails & Skewness)
                cf_pdf = tda.get("cornish_fisher_pdf", tda["pdf_distribution"])
                fig_sb.add_trace(
                    go.Scatter(
                        x=tda["spot_grid"],
                        y=cf_pdf,
                        mode="lines",
                        name=f"Empirical PDF (Skew {sb_skew:+.2f}, Kurt {sb_kurt:+.2f})",
                        line=dict(color="#A855F7", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(168, 85, 247, 0.18)"
                    ),
                    secondary_y=True
                )

                # Trace 4: Gaussian Normal PDF (Thin-Tail Benchmark)
                norm_pdf = tda.get("normal_pdf", tda["pdf_distribution"])
                fig_sb.add_trace(
                    go.Scatter(
                        x=tda["spot_grid"],
                        y=norm_pdf,
                        mode="lines",
                        name="Gaussian Normal PDF (Benchmark)",
                        line=dict(color="#94A3B8", width=1.5, dash="dot")
                    ),
                    secondary_y=True
                )

                # Zero PnL Reference
                fig_sb.add_hline(y=0, line_dash="dash", line_color="#64748B", secondary_y=False)

                # Spot Reference (staggered to top left with dark badge box to eliminate any collision with BE)
                fig_sb.add_vline(
                    x=sb_spot,
                    line_dash="dot",
                    line_color="#F59E0B",
                    annotation_text=f" Spot ${sb_spot:,.2f} ",
                    annotation_position="top left",
                    annotation_font=dict(color="#F59E0B", size=10.5, family="monospace"),
                    annotation_bgcolor="rgba(15, 23, 42, 0.92)",
                    annotation_bordercolor="#F59E0B",
                    annotation_borderwidth=1
                )

                # Breakevens (staggered to bottom right with dark badge box)
                for i, be in enumerate(pm["breakeven_points"]):
                    be_pos = "bottom right" if i % 2 == 0 else "bottom left"
                    fig_sb.add_vline(
                        x=be,
                        line_dash="dot",
                        line_color="#EF4444",
                        annotation_text=f" BE ${be:,.2f} ",
                        annotation_position=be_pos,
                        annotation_font=dict(color="#EF4444", size=10.5, family="monospace"),
                        annotation_bgcolor="rgba(15, 23, 42, 0.92)",
                        annotation_bordercolor="#EF4444",
                        annotation_borderwidth=1
                    )

                # 95% & 99% Cornish-Fisher VaR price markers
                e_cones = econo["standard_deviation_cones"]["econometric_adjusted"]
                cf_var_95_px = e_cones.get("minus_2_sigma_cf")
                cf_var_99_px = e_cones.get("minus_3_sigma_cf")
                if cf_var_95_px and cf_var_95_px > min(tda["spot_grid"]):
                    fig_sb.add_vline(
                        x=cf_var_95_px,
                        line_dash="dashdot",
                        line_color="#EC4899",
                        annotation_text=f" 95% VaR ${cf_var_95_px:,.2f} ",
                        annotation_position="top right",
                        annotation_font=dict(color="#EC4899", size=9.5, family="monospace"),
                        annotation_bgcolor="rgba(15, 23, 42, 0.92)",
                        annotation_bordercolor="#EC4899",
                        annotation_borderwidth=1
                    )

                fig_sb.update_layout(
                    title=dict(
                        text=f"<b>{sb_strat}</b> — Dual PnL & Continuous Econometric Distribution",
                        x=0.01,
                        y=0.98,
                        xanchor="left",
                        yanchor="top",
                        font=dict(size=13, color="#F8FAFC")
                    ),
                    xaxis_title="Underlying Spot Price ($)",
                    yaxis_title="Net Strategy PnL ($)",
                    yaxis2_title="Probability Density",
                    template="plotly_dark",
                    height=420,
                    margin=dict(l=35, r=35, t=75, b=30),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.03,
                        xanchor="right",
                        x=1.0,
                        bgcolor="rgba(15, 23, 42, 0.85)",
                        bordercolor="#334155",
                        borderwidth=1,
                        font=dict(size=10.5, color="#E2E8F0")
                    ),
                    hovermode="x unified"
                )
                st.plotly_chart(fig_sb, use_container_width=True)

                # KPI Row 1: Primary Probability Metrics
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Prob of Profit (POP)", f"{pm['probability_of_profit_pct']:.1f}%", f"Fat-Tail: {pm['econometric_adjusted_pop_pct']:.1f}%")
                k2.metric("Expected Value (EV)", f"${pm['expected_value_usd']:+,.2f}", "Statistical EV")
                k3.metric("Prob Max Profit", f"{pm['prob_max_profit_pct']:.1f}%", f"Max: +${pm['max_profit_usd']:,.2f}")
                k4.metric("Prob Max Loss", f"{pm['prob_max_loss_pct']:.1f}%", f"Max: ${pm['max_loss_usd']:,.2f}")

                # KPI Row 2: Capital Allocation & Touch Probabilities
                k5, k6, k7, k8 = st.columns(4)
                k5.metric("Win / Loss Ratio", f"{pm['win_loss_ratio']:.2f}x", "Profit/Loss Magnitude")
                k6.metric("Half-Kelly Sizing", f"{pm['kelly_fraction_half_pct']:.1f}%", f"Full: {pm['kelly_fraction_full_pct']:.1f}%")
                # Format touch probabilities string
                touch_str = ", ".join([f"{k}: {v}%" for k, v in pm["breakeven_touch_probabilities"].items()]) if pm["breakeven_touch_probabilities"] else "None"
                k7.metric("Touch Probability", touch_str[:25], "Chance of touching BE")
                k8.metric("Structure Net Premium", f"${sb_sim_res['greeks_summary']['net_debit_credit']:,.2f}", sb_sim_res['greeks_summary']['structure'])

            # Comprehensive Key Metrics Breakdown Section
            st.divider()
            st.markdown("#### 🔬 Comprehensive Econometric Key Metrics & Tail Risk Matrix")
            tab_m1, tab_m2, tab_m3, tab_m4, tab_m5 = st.tabs([
                "📊 4-Moment Econometric Matrix",
                "🛡️ Value-at-Risk (VaR) & CVaR (Expected Shortfall)",
                "📐 Standard Deviation Cones: Gaussian vs Cornish-Fisher",
                "🎯 Strategy Decision, Sizing & Greeks",
                "🌐 3D Volatility Surface & SABR Smile"
            ])

            with tab_m1:
                st.markdown("##### 🧮 4-Moment Empirical Return Analysis & Normality Tests")
                m_c1, m_c2, m_c3, m_c4 = st.columns(4)
                m_c1.metric(
                    "1st Moment: Annual Drift (μ)",
                    f"{econo['drift_annualized_pct']:+.2f}%",
                    f"Horizon: {econo['horizon_days']} Days"
                )
                m_c2.metric(
                    "2nd Moment: Volatility (σ)",
                    f"{econo['volatility_annualized_pct']:.2f}%",
                    f"Period σ: {econo['period_volatility_pct']:.2f}%"
                )
                m_c3.metric(
                    "3rd Moment: Sample Skew (S)",
                    f"{econo['skewness']:+.4f}",
                    sb_moments.get("skew_regime", "Crash Asymmetry")[:22]
                )
                m_c4.metric(
                    "4th Moment: Excess Kurtosis (K)",
                    f"{econo['excess_kurtosis']:+.4f}",
                    sb_moments.get("tail_regime", "Leptokurtic")[:22]
                )

                st.markdown("---")
                jb_c1, jb_c2, jb_c3, jb_c4 = st.columns(4)
                jb_c1.metric(
                    "Jarque-Bera Test (JB)",
                    f"{sb_moments.get('jarque_bera_stat', 0.0):,.2f}",
                    "Normality Test"
                )
                jb_c2.metric(
                    "JB p-value",
                    f"{sb_moments.get('jarque_bera_p_value', 0.0):.6f}",
                    "p < 0.05 = Reject Gauss"
                )
                norm_rej = sb_moments.get("normality_rejected", True)
                jb_c3.metric(
                    "Normality Hypothesis",
                    "REJECTED ❌" if norm_rej else "ACCEPTED ✔️",
                    "Fat Tails Proven" if norm_rej else "Gaussian Fit"
                )
                jb_c4.metric(
                    "1-Year Max Drawdown",
                    f"-{sb_moments.get('max_drawdown_pct', 0.0):.2f}%",
                    f"Sharpe: {sb_moments.get('sharpe_ratio_proxy', 0.0):.2f}"
                )

            with tab_m2:
                st.markdown("##### 🛡️ Downside Value-at-Risk (VaR) & Conditional VaR (Expected Shortfall)")
                vm = econo["var_metrics"]
                cm = econo["cvar_expected_shortfall"]
                ta = econo["tail_asymmetry"]

                v_c1, v_c2, v_c3, v_c4 = st.columns(4)
                v_c1.metric(
                    "95% Gaussian VaR",
                    f"{vm['var_normal_95_pct']:.2f}%",
                    f"${vm['var_normal_95_dollars']:,.2f} USD"
                )
                v_c2.metric(
                    "95% Cornish-Fisher VaR",
                    f"{vm['var_cf_95_pct']:.2f}%",
                    f"${vm['var_cf_95_dollars']:,.2f} USD"
                )
                v_c3.metric(
                    "95% Fat-Tail VaR Surcharge",
                    f"+{vm['fat_tail_surcharge_95_pct']:.2f}%",
                    f"+${vm['fat_tail_surcharge_95_dollars']:,.2f} USD"
                )
                v_c4.metric(
                    "95% CVaR (Expected Shortfall)",
                    f"{cm['cvar_cf_95_pct']:.2f}%",
                    f"${cm['cvar_cf_95_dollars']:,.2f} USD"
                )

                st.markdown("---")
                v2_c1, v2_c2, v2_c3, v2_c4 = st.columns(4)
                v2_c1.metric(
                    "99% Gaussian VaR (Extreme)",
                    f"{vm['var_normal_99_pct']:.2f}%",
                    f"${vm['var_normal_99_dollars']:,.2f} USD"
                )
                v2_c2.metric(
                    "99% Cornish-Fisher VaR",
                    f"{vm['var_cf_99_pct']:.2f}%",
                    f"${vm['var_cf_99_dollars']:,.2f} USD"
                )
                v2_c3.metric(
                    "99% Fat-Tail VaR Surcharge",
                    f"+{vm['fat_tail_surcharge_99_pct']:.2f}%",
                    f"+${vm['fat_tail_surcharge_99_dollars']:,.2f} USD"
                )
                v2_c4.metric(
                    "99% CVaR (Expected Shortfall)",
                    f"{cm['cvar_cf_99_pct']:.2f}%",
                    f"${cm['cvar_cf_99_dollars']:,.2f} USD"
                )

                st.caption(f"⚡ **Tail Asymmetry Ratio**: `{ta['tail_asymmetry_ratio']:.2f}x` | **Downside Amplification**: `{ta['downside_amplification']}`. Negative skewness and leptokurtosis cause downside crash risk to significantly exceed upside variance.")

            with tab_m3:
                st.markdown("##### 📐 Standard Deviation Cones: Gaussian vs Cornish-Fisher Expansion")
                norm_cones = econo["standard_deviation_cones"]["normal"]
                cf_cones = econo["standard_deviation_cones"]["econometric_adjusted"]

                st.caption("Side-by-side terminal price bounds at expiration. Notice how Cornish-Fisher pushes lower tail bounds further down and adjusts the upper expansion for skewness:")

                cone_cols = st.columns(7)
                cone_cols[0].metric("-3σ (99.73%)", f"${cf_cones['minus_3_sigma_cf']:,.2f}", f"Gauss: ${norm_cones['minus_3_sigma']:,.2f}")
                cone_cols[1].metric("-2σ (95.45%)", f"${cf_cones['minus_2_sigma_cf']:,.2f}", f"Gauss: ${norm_cones['minus_2_sigma']:,.2f}")
                cone_cols[2].metric("-1σ (68.27%)", f"${cf_cones['minus_1_sigma_cf']:,.2f}", f"Gauss: ${norm_cones['minus_1_sigma']:,.2f}")
                cone_cols[3].metric("Expected Mean", f"${norm_cones['mean_expected']:,.2f}", f"Median: ${norm_cones['median_expected']:,.2f}")
                cone_cols[4].metric("+1σ (68.27%)", f"${cf_cones['plus_1_sigma_cf']:,.2f}", f"Gauss: ${norm_cones['plus_1_sigma']:,.2f}")
                cone_cols[5].metric("+2σ (95.45%)", f"${cf_cones['plus_2_sigma_cf']:,.2f}", f"Gauss: ${norm_cones['plus_2_sigma']:,.2f}")
                cone_cols[6].metric("+3σ (99.73%)", f"${cf_cones['plus_3_sigma_cf']:,.2f}", f"Gauss: ${norm_cones['plus_3_sigma']:,.2f}")

            with tab_m4:
                st.markdown("##### 🎯 Strategy Architecture, Capital Allocation & Greeks Summary")
                gs = sb_sim_res["greeks_summary"]
                g_c1, g_c2, g_c3, g_c4, g_c5 = st.columns(5)
                g_c1.metric("Net Delta (Δ)", f"{gs.get('net_delta', 0.0):+.3f}", "Directional bias")
                g_c2.metric("Net Gamma (Γ)", f"{gs.get('net_gamma', 0.0):+.4f}", "Delta acceleration")
                g_c3.metric("Net Vega (𝒱)", f"{gs.get('net_vega', 0.0):+.2f}", "Per 1% IV shift")
                g_c4.metric("Daily Theta (Θ)", f"${gs.get('net_theta_daily', 0.0):+,.2f}", "Time decay / day")
                g_c5.metric("Net Premium", f"${gs.get('net_debit_credit', 0.0):,.2f}", gs.get("structure", "Spread"))

                st.markdown("---")
                p_c1, p_c2, p_c3, p_c4 = st.columns(4)
                p_c1.metric("Gaussian POP", f"{pm['probability_of_profit_pct']:.1f}%", "Unadjusted")
                p_c2.metric("Fat-Tail Adjusted POP", f"{pm['econometric_adjusted_pop_pct']:.1f}%", f"{pm['econometric_adjusted_pop_pct'] - pm['probability_of_profit_pct']:+.1f}% shift")
                p_c3.metric("Full-Kelly Allocation", f"{pm['kelly_fraction_full_pct']:.1f}%", "Max Theoretical")
                p_c4.metric("Half-Kelly Allocation", f"{pm['kelly_fraction_half_pct']:.1f}%", "Institutional Safe")

            with tab_m5:
                st.markdown("##### 🌐 Parametric SABR Volatility Surface & Smile Analytics")
                surf_data = sb_sim_res.get("volatility_surface_analysis")
                if not surf_data:
                    surf_data = sim_engine.generate_volatility_surface_analysis(sb_spot, ticker=sb_live["symbol"], base_iv=sb_vol_dec)

                s_diag = surf_data.get("diagnostics", {})
                sd_c1, sd_c2, sd_c3, sd_c4 = st.columns(4)
                sd_c1.metric("ATM Implied Vol (30D)", f"{s_diag.get('atm_iv_30d_pct', 0.0):.2f}%", "Base Vol Level")
                sd_c2.metric("25-Delta Proxy Skew", f"{s_diag.get('skew_25d_proxy_pct', 0.0):+.2f}%", "Put IV - Call IV")
                sd_c3.metric("Smile Curvature (Butterfly)", f"{s_diag.get('curvature_butterfly_pct', 0.0):+.2f}%", "Wing Convexity")
                sd_c4.metric("Term Structure Slope", f"{s_diag.get('term_structure_slope_pct', 0.0):+.2f}%", "365D vs 30D ATM")

                st.caption(f"**Smile Regime:** `{s_diag.get('regime_interpretation', 'BALANCED SMILE')}` | Underlying Skewness: `{surf_data.get('underlying_empirical_skewness', 0.0):.3f}` | Excess Kurtosis: `{surf_data.get('underlying_empirical_kurtosis', 0.0):.3f}`")

                st.markdown("---")
                col_chart, col_interp = st.columns([2.2, 1.0])

                with col_chart:
                    st.markdown("###### 📈 Multi-Tenor Volatility Smile Slices")
                    fig_smile = go.Figure()
                    dtes_list = surf_data.get("dtes", [7, 14, 30, 60, 90, 180, 365])
                    matrix = surf_data.get("surface_iv_matrix_pct", [])
                    strikes_list = surf_data.get("strikes", [])

                    colors = ["#38BDF8", "#34D399", "#FBBF24", "#F472B6", "#A78BFA", "#818CF8", "#64748B"]
                    for idx, dte_val in enumerate(dtes_list):
                        if idx < len(matrix):
                            fig_smile.add_trace(go.Scatter(
                                x=strikes_list,
                                y=matrix[idx],
                                mode="lines+markers",
                                name=f"{dte_val} DTE",
                                line=dict(color=colors[idx % len(colors)], width=2),
                                marker=dict(size=4)
                            ))

                    fig_smile.add_vline(x=sb_spot, line_dash="dash", line_color="#E2E8F0", annotation_text="Spot")
                    fig_smile.update_layout(
                        title=f"SABR Volatility Smile Curves: {sb_live['symbol']} (Spot: ${sb_spot:,.2f})",
                        xaxis_title="Strike Price ($ USD)",
                        yaxis_title="Implied Volatility (%)",
                        plot_bgcolor="rgba(15,23,42,0.8)",
                        paper_bgcolor="rgba(15,23,42,0)",
                        font=dict(color="#E2E8F0"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_smile, use_container_width=True)

                with col_interp:
                    st.markdown("###### 🔍 Strike Volatility Interpolator")
                    interp_k = st.number_input("Query Strike ($)", value=float(sb_spot), step=1.0, key=f"q_k_{sb_live['symbol']}")
                    interp_dte = st.slider("Query DTE (Days)", 1, 365, int(sb_dte), key=f"q_dte_{sb_live['symbol']}")

                    # Query dynamic volatility surface
                    from tools.calc.volatility_surface import VolatilitySurfaceEngine
                    q_surf = VolatilitySurfaceEngine(spot=sb_spot, risk_free_rate=sb_r_dec)
                    q_surf.fit_synthetic_surface(base_atm_iv=sb_vol_dec, skew_sentiment="bearish_skew" if sb_skew < -0.2 else "neutral_smile")
                    q_iv = q_surf.get_implied_volatility(strike=interp_k, dte_days=interp_dte)

                    st.metric("Interpolated SABR Volatility", f"{q_iv * 100.0:.2f}%", f"{q_iv * 100.0 - sb_iv:+.2f}% vs ATM")
                    st.metric("Log-Moneyness ln(K/S)", f"{math.log(max(0.01, interp_k) / sb_spot):+.3f}", "OTM Put" if interp_k < sb_spot else "OTM Call")

                    # Greek price check
                    from tools.calc.derivatives_math import BlackScholesEngine
                    bs_call = BlackScholesEngine.price_and_greeks(sb_spot, interp_k, interp_dte / 365.0, sb_r_dec, q_iv, option_type="call")
                    bs_put = BlackScholesEngine.price_and_greeks(sb_spot, interp_k, interp_dte / 365.0, sb_r_dec, q_iv, option_type="put")
                    st.caption(f"**Smile BSM Fair Value:** Call: `${bs_call['price']:,.2f}` | Put: `${bs_put['price']:,.2f}`")

            # -----------------------------------------------------------------
            # MULTI-AGENT INVESTMENT COMMITTEE REVIEW & ADVERSARIAL AUDIT
            # -----------------------------------------------------------------
            st.divider()
            st.markdown("#### 🏛️ Multi-Agent Investment Committee Review & Adversarial Stress Audit")
            st.caption("Convene the autonomous Multi-Asset Investment Committee: Options Greek Strategist, Cross-Asset Risk Officer, and Skeptic Agent debate the strategy live, evaluate non-Gaussian tail risk, and issue a binding audit verdict.")

            comm_col1, comm_col2 = st.columns([1.5, 2.5])
            with comm_col1:
                run_comm_btn = st.button(
                    "🏛️ CONVENE INVESTMENT COMMITTEE REVIEW",
                    type="secondary",
                    use_container_width=True,
                    key=f"btn_comm_opt_{sb_live['symbol']}"
                )
            with comm_col2:
                st.caption("Autonomous Gatekeeping: Synthesizes quantitative Greeks, Cornish-Fisher VaR surcharge, and Skeptic adversarial challenges into a cryptographic provenance dossier.")

            comm_key = f"comm_review_opt_{sb_live['symbol']}"
            if run_comm_btn:
                with st.spinner("Convening Multi-Agent Investment Committee & synthesizing adversarial audit..."):
                    orchestrator = MeridianMultiAssetOrchestrator()
                    comm_res = orchestrator.evaluate_strategy_deal_committee(
                        symbol=sb_live["symbol"],
                        strategy_name=sb_strat,
                        spot_price=sb_spot,
                        legs=sb_legs,
                        risk_free_rate=sb_r_dec,
                        custom_volatility=sb_vol_dec,
                        custom_drift=sb_drift,
                        custom_skewness=sb_skew,
                        custom_kurtosis=sb_kurt,
                        target_days=sb_target_day,
                        iv_shift_pct=sb_iv_shift
                    )
                    st.session_state[comm_key] = comm_res

            if comm_key in st.session_state:
                c_res = st.session_state[comm_key]
                v_color = "#10B981" if c_res["verdict"] == "APPROVED" else ("#F59E0B" if c_res["verdict"] == "CONDITIONAL_APPROVAL" else "#EF4444")
                v_badge = "🟢 APPROVED" if c_res["verdict"] == "APPROVED" else ("🟡 CONDITIONAL APPROVAL" if c_res["verdict"] == "CONDITIONAL_APPROVAL" else "🔴 REJECTED")

                st.markdown(f"""
                <div style="background:rgba(15,23,42,0.85); border:2px solid {v_color}; border-radius:8px; padding:14px 18px; margin:12px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                        <span style="font-weight:800; font-size:1.05rem; color:{v_color};">
                            {v_badge} — Investment Committee Consensus
                        </span>
                        <span style="font-family:monospace; font-weight:700; color:#F8FAFC; font-size:0.92rem;">
                            Committee Confidence: <b>{c_res['confidence_score']:.1f}/100</b> | ID: <code>{c_res['provenance_ledger_id'][:18]}...</code>
                        </span>
                    </div>
                    <div style="color:#CBD5E1; font-size:0.86rem; margin-top:6px;">
                        {c_res['verdict_rationale']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 3-Agent Committee Perspectives
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("##### 🎯 Options Greek Strategist")
                    st.caption("Derivative Greeks & Payoff Structure")
                    st.write(f"• **Net Delta**: `{gs.get('net_delta', 0.0):+.3f}` | **Gamma**: `{gs.get('net_gamma', 0.0):+.4f}`")
                    st.write(f"• **Net Vega**: `{gs.get('net_vega', 0.0):+.2f}` | **Theta**: `${gs.get('net_theta_daily', 0.0):+,.2f}/day`")
                    st.write(f"• **Gaussian POP**: `{pm['probability_of_profit_pct']:.1f}%`")
                    st.write(f"• **Half-Kelly Sizing**: `{pm['kelly_fraction_half_pct']:.1f}%`")

                with c2:
                    st.markdown("##### 🛡️ Cross-Asset Risk Officer")
                    st.caption("Cornish-Fisher Tail Risk & VaR Surcharge")
                    cro_d = c_res["desk_reports"]["Cross-Asset Risk Officer"]
                    st.write(f"• **Tail Status**: `{cro_d.get('verdict', 'MONITORED')}`")
                    st.write(f"• **95% CF VaR**: `${econo['var_metrics']['var_cf_95_dollars']:,.2f}` (`{econo['var_metrics']['var_cf_95_pct']:.2f}%`)")
                    st.write(f"• **Fat-Tail Surcharge**: `+${econo['var_metrics']['fat_tail_surcharge_95_dollars']:,.2f}` (`+{econo['var_metrics']['fat_tail_surcharge_95_pct']:.2f}%`)")
                    st.write(f"• **Tail Asymmetry**: `{econo['tail_asymmetry']['tail_asymmetry_ratio']:.2f}x`")

                with c3:
                    st.markdown("##### 🕵️ Skeptic Adversarial Agent")
                    st.caption("Stress Tests & Counter-Theses")
                    sk_d = c_res["desk_reports"]["Skeptic Agent"]
                    st.write(f"• **Skeptic Verdict**: `{sk_d.get('skeptic_verdict', 'CONCUR')}`")
                    st.write(f"• **Adversarial Score**: `{sk_d.get('skeptic_score', 75.0):.1f}/100`")
                    challs = sk_d.get("adversarial_challenges", [])
                    if challs:
                        for ch in challs[:2]:
                            st.write(f"• ⚠️ **{ch['challenge']}**: {ch['argument'][:60]}...")
                    else:
                        st.write("• ✔️ No critical structural thesis objections found.")

                if c_res.get("mitigations"):
                    st.markdown("**Actionable Risk Mitigations Recommended by Committee:**")
                    for m in c_res["mitigations"]:
                        st.info(f"🛡️ {m}")

            # -----------------------------------------------------------------
            # LIVE DEAL EXECUTION DESK ($1,000,000 SIMULATION CAPITAL)
            # -----------------------------------------------------------------
            st.divider()
            st.markdown("#### ⚡ Execute Evaluated Deal into Portfolio ($1,000,000 Simulation Capital)")
            pe_sb = get_paper_trading_engine()
            p_data_sb = pe_sb.load_portfolio()
            p_cash_sb = float(p_data_sb.get("cash_balance", INITIAL_PORTFOLIO_CASH))

            sc1, sc2, sc3 = st.columns([1, 1, 1.5])
            with sc1:
                sb_trade_action = st.radio("Trade Action", ["BUY to Open", "SELL to Open"], horizontal=True, key=f"sb_trade_act_{sb_live['symbol']}")
            with sc2:
                sb_trade_qty = st.number_input("Contracts Quantity", min_value=1, max_value=1000, value=1, step=1, key=f"sb_trade_q_{sb_live['symbol']}")
            with sc3:
                clean_sb_side = "BUY" if "BUY" in sb_trade_action else "SELL"
                sb_debit = abs(sb_sim_res["greeks_summary"]["net_debit_credit"])
                sb_tot_cost = sb_trade_qty * sb_debit * 100.0
                active_venue_sb = st.session_state.get("active_routing_venue", "SMART")
                active_mode_sb = st.session_state.get("active_execution_mode", "SIMULATION_PAPER")
                tca_sb = ExecutionCostModel.calculate_execution_costs(
                    asset_class="Options",
                    side=clean_sb_side,
                    quantity=float(sb_trade_qty),
                    price=float(sb_debit)
                )
                st.caption(f"Required Outlay: **${sb_tot_cost:,.2f} USD** | Venue: <b style='color:#38BDF8;'>{active_venue_sb}</b> | Est TCA Friction: **${tca_sb['total_friction_usd']:,.2f} USD**")
                if st.button("🟢 EXECUTE SIMULATION STRATEGY AT MARKET ($)", type="primary", use_container_width=True, key=f"sb_exec_btn_{sb_live['symbol']}"):
                    c_notes = ""
                    if comm_key in st.session_state:
                        c_info = st.session_state[comm_key]
                        c_notes = f"Committee: {c_info['verdict']} ({c_info['confidence_score']:.0f}/100) | "

                    s_ok, s_msg, s_pos = pe_sb.execute_trade(
                        symbol=sb_live["symbol"],
                        asset_class="Options",
                        side=clean_sb_side,
                        quantity=float(sb_trade_qty),
                        price=float(sb_debit),
                        strategy_type=f"{sb_strat} (Simulator)",
                        multiplier=100.0,
                        routing_venue=active_venue_sb,
                        execution_mode=active_mode_sb,
                        notes=f"{c_notes}Simulated POP: {pm['probability_of_profit_pct']:.1f}%, EV: ${pm['expected_value_usd']:,.2f}"
                    )
                    if s_ok:
                        st.success(s_msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(s_msg)

        # ---------------------------------------------------------------------
        # 2. EQUITIES & SINGLE STOCKS (TARGET VS STOP-LOSS TOUCH RISK)
        # ---------------------------------------------------------------------
        elif "Equities" in sim_asset_mode:
            st.markdown("#### 📈 Single-Stock Probability of Touch & Execution Risk")
            eq_s_col1, eq_s_col2 = st.columns([2.5, 1])
            with eq_s_col1:
                eq_query = st.text_input(
                    "Company Name or Symbol",
                    value=st.session_state.get("eq_query_val", "MU"),
                    key="eq_query_in",
                    help="Type company name (e.g. micron, apple, nvidia) or symbol (e.g. MU, AAPL)"
                )
            with eq_s_col2:
                st.write("")
                st.write("")
                if st.button("🔄 Sync Live", key="eq_sync_btn", use_container_width=True):
                    st.rerun()

            eq_live = resolve_and_fetch_live_asset(eq_query)
            st.session_state["eq_query_val"] = eq_live["symbol"]

            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.12); border:1px solid #10B981; border-radius:6px; padding:8px 12px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:800; color:#F8FAFC; font-size:0.88rem;">
                        🟢 {eq_live['name']} ({eq_live['symbol']})
                    </span>
                    <span style="font-family:monospace; font-weight:800; color:#10B981; font-size:1.02rem;">
                        ${eq_live['price']:,.2f} USD ({eq_live['change_pct']:+.2f}%)
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            eq_moments = get_cached_empirical_moments(eq_live["symbol"])

            eq_calib_mode = st.radio(
                "Econometric Calibration Engine",
                [
                    "📡 Auto-Calibrated (252d Live Return Moments)",
                    "🎛️ Interactive Custom Scenario (Manual Sliders)"
                ],
                horizontal=True,
                key=f"eq_calib_mode_{eq_live['symbol']}"
            )

            if eq_calib_mode.startswith("📡"):
                eq_skew = float(eq_moments["sample_skewness"])
                eq_kurt = float(eq_moments["sample_excess_kurtosis"])
                eq_drift = float(eq_moments["annualized_drift"])
                eq_vol = float(eq_moments["annualized_volatility"])
                st.markdown(f"""
                <div style="background:rgba(168,85,247,0.10); border:1px solid #A855F7; border-radius:6px; padding:8px 12px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#F8FAFC; font-size:0.82rem;">
                            🔬 252d Return Moments ({eq_moments['tail_regime'][:24]}):
                        </span>
                        <span style="font-family:monospace; font-weight:700; color:#A855F7; font-size:0.82rem;">
                            Skew: {eq_skew:+.2f} | Kurt: {eq_kurt:+.2f} | Drift: {eq_moments['annualized_drift_pct']:+.1f}% | Vol: {eq_moments['annualized_volatility_pct']:.1f}%
                        </span>
                    </div>
                    <div style="font-size:0.75rem; color:#94A3B8; margin-top:3px;">
                        Jarque-Bera: <b>{eq_moments['jarque_bera_stat']:,.1f}</b> (p={eq_moments['jarque_bera_p_value']:.4f}) — <b>{'Normality REJECTED' if eq_moments['normality_rejected'] else 'Normal Accepted'}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption("🎛️ Interactive sliders directly warp the probability curves and metrics in real time:")
                e_s1, e_s2, e_s3, e_s4 = st.columns(4)
                with e_s1:
                    eq_skew = st.slider("Sample Skewness", -2.50, 1.50, float(eq_moments["sample_skewness"]), 0.05, key=f"eq_skew_sl_{eq_live['symbol']}")
                with e_s2:
                    eq_kurt = st.slider("Excess Kurtosis", 0.0, 10.0, max(0.0, float(eq_moments["sample_excess_kurtosis"])), 0.10, key=f"eq_kurt_sl_{eq_live['symbol']}")
                with e_s3:
                    eq_drift_pct = st.slider("Annual Drift (%)", -50.0, 50.0, float(eq_moments["annualized_drift_pct"]), 0.5, key=f"eq_drift_sl_{eq_live['symbol']}")
                    eq_drift = eq_drift_pct / 100.0
                with e_s4:
                    eq_vol_pct = st.slider("Volatility (%)", 5.0, 200.0, float(eq_moments["annualized_volatility_pct"]), 0.5, key=f"eq_vol_sl_{eq_live['symbol']}")
                    eq_vol = eq_vol_pct / 100.0

            eq_c1, eq_c2, eq_c3, eq_c4 = st.columns(4)
            with eq_c1:
                eq_sp = st.number_input("Current Stock Price ($)", min_value=0.1, value=float(eq_live["price"]), step=1.0, format="%.2f", key=f"eq_sp_{eq_live['symbol']}")
            with eq_c2:
                eq_tp = st.number_input("Profit Target Price ($)", min_value=0.1, value=round(float(eq_sp * 1.15), 2), step=1.0, format="%.2f", key=f"eq_tp_{eq_live['symbol']}")
            with eq_c3:
                eq_sl = st.number_input("Stop Loss Price ($)", min_value=0.1, value=round(float(eq_sp * 0.90), 2), step=1.0, format="%.2f", key=f"eq_sl_{eq_live['symbol']}")
            with eq_c4:
                eq_hor = st.number_input("Horizon (Days)", min_value=5, value=60, step=5, key=f"eq_hor_{eq_live['symbol']}")

            eq_sim = sim_engine.simulate_equity_probability(
                spot=eq_sp,
                target_price=eq_tp,
                stop_loss_price=eq_sl,
                horizon_days=eq_hor,
                volatility=eq_vol,
                drift=eq_drift,
                skewness=eq_skew,
                kurtosis=eq_kurt
            )

            # Equity Dual Distribution Chart
            eq_curves = eq_sim["distribution_curves"]
            eq_econo = eq_sim["econometric_metrics"]
            fig_eq = go.Figure()

            fig_eq.add_trace(go.Scatter(
                x=eq_curves["spot_grid"],
                y=eq_curves["cornish_fisher_pdf"],
                mode="lines",
                name=f"Empirical PDF (Skew {eq_skew:+.2f}, Kurt {eq_kurt:+.2f})",
                line=dict(color="#A855F7", width=2),
                fill="tozeroy",
                fillcolor="rgba(168, 85, 247, 0.18)"
            ))

            fig_eq.add_trace(go.Scatter(
                x=eq_curves["spot_grid"],
                y=eq_curves["normal_pdf"],
                mode="lines",
                name="Gaussian Normal PDF (Benchmark)",
                line=dict(color="#94A3B8", width=1.5, dash="dot")
            ))

            # Reference Lines
            fig_eq.add_vline(
                x=eq_sp,
                line_dash="dot",
                line_color="#F59E0B",
                annotation_text=f" Spot ${eq_sp:,.2f} ",
                annotation_position="top left",
                annotation_font=dict(color="#F59E0B", size=10.5, family="monospace"),
                annotation_bgcolor="rgba(15, 23, 42, 0.92)",
                annotation_bordercolor="#F59E0B",
                annotation_borderwidth=1
            )

            fig_eq.add_vline(
                x=eq_tp,
                line_dash="dash",
                line_color="#10B981",
                annotation_text=f" Target ${eq_tp:,.2f} ",
                annotation_position="top right",
                annotation_font=dict(color="#10B981", size=10.5, family="monospace"),
                annotation_bgcolor="rgba(15, 23, 42, 0.92)",
                annotation_bordercolor="#10B981",
                annotation_borderwidth=1
            )

            fig_eq.add_vline(
                x=eq_sl,
                line_dash="dash",
                line_color="#EF4444",
                annotation_text=f" Stop Loss ${eq_sl:,.2f} ",
                annotation_position="bottom left",
                annotation_font=dict(color="#EF4444", size=10.5, family="monospace"),
                annotation_bgcolor="rgba(15, 23, 42, 0.92)",
                annotation_bordercolor="#EF4444",
                annotation_borderwidth=1
            )

            eq_cones_cf = eq_econo["standard_deviation_cones"]["econometric_adjusted"]
            eq_var_95_px = eq_cones_cf.get("minus_2_sigma_cf")
            if eq_var_95_px and eq_var_95_px > min(eq_curves["spot_grid"]):
                fig_eq.add_vline(
                    x=eq_var_95_px,
                    line_dash="dashdot",
                    line_color="#EC4899",
                    annotation_text=f" 95% VaR ${eq_var_95_px:,.2f} ",
                    annotation_position="bottom right",
                    annotation_font=dict(color="#EC4899", size=9.5, family="monospace"),
                    annotation_bgcolor="rgba(15, 23, 42, 0.92)",
                    annotation_bordercolor="#EC4899",
                    annotation_borderwidth=1
                )

            fig_eq.update_layout(
                title=dict(
                    text=f"<b>{eq_live['symbol']}</b> — Continuous Horizon Return Distribution & Barrier Levels",
                    x=0.01,
                    y=0.98,
                    xanchor="left",
                    yanchor="top",
                    font=dict(size=13, color="#F8FAFC")
                ),
                xaxis_title="Stock Price ($)",
                yaxis_title="Probability Density",
                template="plotly_dark",
                height=380,
                margin=dict(l=35, r=35, t=65, b=30),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.03,
                    xanchor="right",
                    x=1.0,
                    bgcolor="rgba(15, 23, 42, 0.85)",
                    bordercolor="#334155",
                    borderwidth=1,
                    font=dict(size=10.5, color="#E2E8F0")
                ),
                hovermode="x unified"
            )
            st.plotly_chart(fig_eq, use_container_width=True)

            e1, e2, e3, e4, e5 = st.columns(5)
            e1.metric("Prob Touch Target", f"{eq_sim['prob_touch_target_pct']:.1f}%", f"+{eq_sim['target_upside_pct']:.1f}% gain")
            e2.metric("Prob Touch Stop Loss", f"{eq_sim['prob_touch_stop_loss_pct']:.1f}%", f"{eq_sim['stop_loss_pct']:.1f}% loss")
            e3.metric("Prob Close Above Target", f"{eq_sim['prob_close_above_target_pct']:.1f}%", f"Fat-Tail: {eq_sim['econometric_prob_above_target_pct']:.1f}%")
            e4.metric("Risk / Reward Ratio", f"{eq_sim['risk_reward_ratio']:.2f}x", "Target/Stop Distance")
            e5.metric("Evaluation Horizon", f"{eq_hor} Days", f"Drift: {eq_econo['drift_annualized_pct']:+.1f}%")

            # Comprehensive Key Metrics Breakdown Section for Equities
            st.divider()
            st.markdown("#### 🔬 Single-Stock Econometric Tail Risk Matrix")
            eq_tab_m1, eq_tab_m2, eq_tab_m3 = st.tabs([
                "📊 4-Moment Return Matrix",
                "🛡️ Value-at-Risk (VaR) & CVaR (Expected Shortfall)",
                "📐 Standard Deviation Cones: Gaussian vs Cornish-Fisher"
            ])

            with eq_tab_m1:
                st.markdown("##### 🧮 4-Moment Empirical Return Analysis & Normality Tests")
                em_c1, em_c2, em_c3, em_c4 = st.columns(4)
                em_c1.metric(
                    "1st Moment: Annual Drift (μ)",
                    f"{eq_econo['drift_annualized_pct']:+.2f}%",
                    f"Horizon: {eq_econo['horizon_days']} Days"
                )
                em_c2.metric(
                    "2nd Moment: Volatility (σ)",
                    f"{eq_econo['volatility_annualized_pct']:.2f}%",
                    f"Period σ: {eq_econo['period_volatility_pct']:.2f}%"
                )
                em_c3.metric(
                    "3rd Moment: Sample Skew (S)",
                    f"{eq_econo['skewness']:+.4f}",
                    eq_moments.get("skew_regime", "Crash Asymmetry")[:22]
                )
                em_c4.metric(
                    "4th Moment: Excess Kurtosis (K)",
                    f"{eq_econo['excess_kurtosis']:+.4f}",
                    eq_moments.get("tail_regime", "Leptokurtic")[:22]
                )

                st.markdown("---")
                ejb_c1, ejb_c2, ejb_c3, ejb_c4 = st.columns(4)
                ejb_c1.metric(
                    "Jarque-Bera Test (JB)",
                    f"{eq_moments.get('jarque_bera_stat', 0.0):,.2f}",
                    "Normality Test"
                )
                ejb_c2.metric(
                    "JB p-value",
                    f"{eq_moments.get('jarque_bera_p_value', 0.0):.6f}",
                    "p < 0.05 = Reject Gauss"
                )
                eq_norm_rej = eq_moments.get("normality_rejected", True)
                ejb_c3.metric(
                    "Normality Hypothesis",
                    "REJECTED ❌" if eq_norm_rej else "ACCEPTED ✔️",
                    "Fat Tails Proven" if eq_norm_rej else "Gaussian Fit"
                )
                ejb_c4.metric(
                    "1-Year Max Drawdown",
                    f"-{eq_moments.get('max_drawdown_pct', 0.0):.2f}%",
                    f"Sharpe: {eq_moments.get('sharpe_ratio_proxy', 0.0):.2f}"
                )

            with eq_tab_m2:
                st.markdown("##### 🛡️ Downside Value-at-Risk (VaR) & Conditional VaR (Expected Shortfall)")
                evm = eq_econo["var_metrics"]
                ecm = eq_econo["cvar_expected_shortfall"]
                eta = eq_econo["tail_asymmetry"]

                ev_c1, ev_c2, ev_c3, ev_c4 = st.columns(4)
                ev_c1.metric("95% Gaussian VaR", f"{evm['var_normal_95_pct']:.2f}%", f"${evm['var_normal_95_dollars']:,.2f} USD")
                ev_c2.metric("95% Cornish-Fisher VaR", f"{evm['var_cf_95_pct']:.2f}%", f"${evm['var_cf_95_dollars']:,.2f} USD")
                ev_c3.metric("95% Fat-Tail Surcharge", f"+{evm['fat_tail_surcharge_95_pct']:.2f}%", f"+${evm['fat_tail_surcharge_95_dollars']:,.2f} USD")
                ev_c4.metric("95% CVaR (Expected Shortfall)", f"{ecm['cvar_cf_95_pct']:.2f}%", f"${ecm['cvar_cf_95_dollars']:,.2f} USD")

                st.markdown("---")
                ev2_c1, ev2_c2, ev2_c3, ev2_c4 = st.columns(4)
                ev2_c1.metric("99% Gaussian VaR (Extreme)", f"{evm['var_normal_99_pct']:.2f}%", f"${evm['var_normal_99_dollars']:,.2f} USD")
                ev2_c2.metric("99% Cornish-Fisher VaR", f"{evm['var_cf_99_pct']:.2f}%", f"${evm['var_cf_99_dollars']:,.2f} USD")
                ev2_c3.metric("99% Fat-Tail Surcharge", f"+{evm['fat_tail_surcharge_99_pct']:.2f}%", f"+${evm['fat_tail_surcharge_99_dollars']:,.2f} USD")
                ev2_c4.metric("99% CVaR (Expected Shortfall)", f"{ecm['cvar_cf_99_pct']:.2f}%", f"${ecm['cvar_cf_99_dollars']:,.2f} USD")

                st.caption(f"⚡ **Tail Asymmetry Ratio**: `{eta['tail_asymmetry_ratio']:.2f}x` | **Downside Amplification**: `{eta['downside_amplification']}`.")

            with eq_tab_m3:
                st.markdown("##### 📐 Standard Deviation Cones: Gaussian vs Cornish-Fisher Expansion")
                eq_norm_cones = eq_econo["standard_deviation_cones"]["normal"]
                eq_cf_cones = eq_econo["standard_deviation_cones"]["econometric_adjusted"]

                cone_cols = st.columns(7)
                cone_cols[0].metric("-3σ (99.73%)", f"${eq_cf_cones['minus_3_sigma_cf']:,.2f}", f"Gauss: ${eq_norm_cones['minus_3_sigma']:,.2f}")
                cone_cols[1].metric("-2σ (95.45%)", f"${eq_cf_cones['minus_2_sigma_cf']:,.2f}", f"Gauss: ${eq_norm_cones['minus_2_sigma']:,.2f}")
                cone_cols[2].metric("-1σ (68.27%)", f"${eq_cf_cones['minus_1_sigma_cf']:,.2f}", f"Gauss: ${eq_norm_cones['minus_1_sigma']:,.2f}")
                cone_cols[3].metric("Expected Mean", f"${eq_norm_cones['mean_expected']:,.2f}", f"Median: ${eq_norm_cones['median_expected']:,.2f}")
                cone_cols[4].metric("+1σ (68.27%)", f"${eq_cf_cones['plus_1_sigma_cf']:,.2f}", f"Gauss: ${eq_norm_cones['plus_1_sigma']:,.2f}")
                cone_cols[5].metric("+2σ (95.45%)", f"${eq_cf_cones['plus_2_sigma_cf']:,.2f}", f"Gauss: ${eq_norm_cones['plus_2_sigma']:,.2f}")
                cone_cols[6].metric("+3σ (99.73%)", f"${eq_cf_cones['plus_3_sigma_cf']:,.2f}", f"Gauss: ${eq_norm_cones['plus_3_sigma']:,.2f}")

            # -----------------------------------------------------------------
            # MULTI-AGENT INVESTMENT COMMITTEE REVIEW & ADVERSARIAL AUDIT
            # -----------------------------------------------------------------
            st.divider()
            st.markdown("#### 🏛️ Multi-Agent Investment Committee Review & Adversarial Stress Audit")
            st.caption("Convene the autonomous Multi-Asset Investment Committee: Equity Risk Specialist, Cross-Asset Risk Officer, and Skeptic Agent debate the position live, stress-testing stop-loss touch probability and tail asymmetry.")

            eq_comm_col1, eq_comm_col2 = st.columns([1.5, 2.5])
            with eq_comm_col1:
                run_eq_comm_btn = st.button(
                    "🏛️ CONVENE INVESTMENT COMMITTEE REVIEW",
                    type="secondary",
                    use_container_width=True,
                    key=f"btn_comm_eq_{eq_live['symbol']}"
                )
            with eq_comm_col2:
                st.caption("Autonomous Gatekeeping: Evaluates upside/downside touch probabilities, Cornish-Fisher VaR surcharge, and Skeptic adversarial challenges.")

            eq_comm_key = f"comm_review_eq_{eq_live['symbol']}"
            if run_eq_comm_btn:
                with st.spinner("Convening Multi-Agent Investment Committee & synthesizing adversarial audit..."):
                    orchestrator = MeridianMultiAssetOrchestrator()
                    eq_comm_res = orchestrator.evaluate_strategy_deal_committee(
                        symbol=eq_live["symbol"],
                        strategy_name=f"Equity Shares ({eq_live['symbol']})",
                        spot_price=eq_sp,
                        target_price=eq_tp,
                        stop_loss_price=eq_sl,
                        horizon_days=eq_hor,
                        custom_volatility=eq_vol,
                        custom_drift=eq_drift,
                        custom_skewness=eq_skew,
                        custom_kurtosis=eq_kurt
                    )
                    st.session_state[eq_comm_key] = eq_comm_res

            if eq_comm_key in st.session_state:
                eq_c_res = st.session_state[eq_comm_key]
                eq_v_color = "#10B981" if eq_c_res["verdict"] == "APPROVED" else ("#F59E0B" if eq_c_res["verdict"] == "CONDITIONAL_APPROVAL" else "#EF4444")
                eq_v_badge = "🟢 APPROVED" if eq_c_res["verdict"] == "APPROVED" else ("🟡 CONDITIONAL APPROVAL" if eq_c_res["verdict"] == "CONDITIONAL_APPROVAL" else "🔴 REJECTED")

                st.markdown(f"""
                <div style="background:rgba(15,23,42,0.85); border:2px solid {eq_v_color}; border-radius:8px; padding:14px 18px; margin:12px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                        <span style="font-weight:800; font-size:1.05rem; color:{eq_v_color};">
                            {eq_v_badge} — Investment Committee Consensus
                        </span>
                        <span style="font-family:monospace; font-weight:700; color:#F8FAFC; font-size:0.92rem;">
                            Committee Confidence: <b>{eq_c_res['confidence_score']:.1f}/100</b> | ID: <code>{eq_c_res['provenance_ledger_id'][:18]}...</code>
                        </span>
                    </div>
                    <div style="color:#CBD5E1; font-size:0.86rem; margin-top:6px;">
                        {eq_c_res['verdict_rationale']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 3-Agent Committee Perspectives
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    st.markdown("##### 📈 Equities Specialist")
                    st.caption("Barrier Touch & Expectancy")
                    st.write(f"• **Target Touch**: `{eq_sim['prob_touch_target_pct']:.1f}%` (+{eq_sim['target_upside_pct']:.1f}%)")
                    st.write(f"• **Stop Loss Touch**: `{eq_sim['prob_touch_stop_loss_pct']:.1f}%` ({eq_sim['stop_loss_pct']:.1f}%)")
                    st.write(f"• **Risk/Reward**: `{eq_sim['risk_reward_ratio']:.2f}x`")
                    st.write(f"• **Expected Horizon**: `{eq_hor} Days`")

                with ec2:
                    st.markdown("##### 🛡️ Cross-Asset Risk Officer")
                    st.caption("Cornish-Fisher Tail Risk & VaR Surcharge")
                    eq_cro_d = eq_c_res["desk_reports"]["Cross-Asset Risk Officer"]
                    st.write(f"• **Tail Status**: `{eq_cro_d.get('verdict', 'MONITORED')}`")
                    st.write(f"• **95% CF VaR**: `${eq_econo['var_metrics']['var_cf_95_dollars']:,.2f}` (`{eq_econo['var_metrics']['var_cf_95_pct']:.2f}%`)")
                    st.write(f"• **Fat-Tail Surcharge**: `+${eq_econo['var_metrics']['fat_tail_surcharge_95_dollars']:,.2f}` (`+{eq_econo['var_metrics']['fat_tail_surcharge_95_pct']:.2f}%`)")
                    st.write(f"• **Tail Asymmetry**: `{eq_econo['tail_asymmetry']['tail_asymmetry_ratio']:.2f}x`")

                with ec3:
                    st.markdown("##### 🕵️ Skeptic Adversarial Agent")
                    st.caption("Stress Tests & Counter-Theses")
                    eq_sk_d = eq_c_res["desk_reports"]["Skeptic Agent"]
                    st.write(f"• **Skeptic Verdict**: `{eq_sk_d.get('skeptic_verdict', 'CONCUR')}`")
                    st.write(f"• **Adversarial Score**: `{eq_sk_d.get('skeptic_score', 75.0):.1f}/100`")
                    eq_challs = eq_sk_d.get("adversarial_challenges", [])
                    if eq_challs:
                        for ch in eq_challs[:2]:
                            st.write(f"• ⚠️ **{ch['challenge']}**: {ch['argument'][:60]}...")
                    else:
                        st.write("• ✔️ No critical structural thesis objections found.")

                if eq_c_res.get("mitigations"):
                    st.markdown("**Actionable Risk Mitigations Recommended by Committee:**")
                    for m in eq_c_res["mitigations"]:
                        st.info(f"🛡️ {m}")

            # Quick Equity Trade Execution
            st.markdown("##### ⚡ Execute Stock Shares into Portfolio ($1,000,000 Capital Balance)")
            pe_eq = get_paper_trading_engine()
            eq_port = pe_eq.load_portfolio()
            eq_cash = float(eq_port.get("cash_balance", INITIAL_PORTFOLIO_CASH))

            eq_b1, eq_b2, eq_b3 = st.columns([1, 1, 1.5])
            with eq_b1:
                eq_side = st.radio("Side", ["BUY (Long)", "SELL (Short)"], horizontal=True, key=f"eq_side_{eq_live['symbol']}")
            with eq_b2:
                eq_qty = st.number_input("Shares", min_value=1, max_value=1000, value=50, step=10, key=f"eq_qty_{eq_live['symbol']}")
            with eq_b3:
                clean_eq_side = "BUY" if "BUY" in eq_side else "SELL"
                eq_outlay = eq_qty * eq_sp
                active_venue_eq = st.session_state.get("active_routing_venue", "SMART")
                active_mode_eq = st.session_state.get("active_execution_mode", "SIMULATION_PAPER")
                tca_eq = ExecutionCostModel.calculate_execution_costs(
                    asset_class="Equities",
                    side=clean_eq_side,
                    quantity=float(eq_qty),
                    price=float(eq_sp)
                )
                st.caption(f"Required Outlay: **${eq_outlay:,.2f} USD** | Venue: <b style='color:#38BDF8;'>{active_venue_eq}</b> | Est TCA Friction: **${tca_eq['total_friction_usd']:,.2f} USD**")
                if st.button("🟢 EXECUTE SHARES ORDER ($)", type="primary", use_container_width=True, key=f"btn_eq_exec_{eq_live['symbol']}"):
                    eq_c_notes = ""
                    if eq_comm_key in st.session_state:
                        eq_c_info = st.session_state[eq_comm_key]
                        eq_c_notes = f"Committee: {eq_c_info['verdict']} ({eq_c_info['confidence_score']:.0f}/100) | "

                    eq_ok, eq_msg, eq_pos = pe_eq.execute_trade(
                        symbol=eq_live["symbol"],
                        asset_class="Equities",
                        side=clean_eq_side,
                        quantity=float(eq_qty),
                        price=float(eq_sp),
                        strategy_type="Equity Position",
                        multiplier=1.0,
                        routing_venue=active_venue_eq,
                        execution_mode=active_mode_eq,
                        notes=f"{eq_c_notes}Target: ${eq_tp:.2f}, SL: ${eq_sl:.2f}"
                    )
                    if eq_ok:
                        st.success(eq_msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(eq_msg)

        # ---------------------------------------------------------------------
        # 3. FUTURES & COMMODITIES (ROLL HORIZON & MARGIN CALL PROBABILITY)
        # ---------------------------------------------------------------------
        elif "Futures" in sim_asset_mode:
            st.markdown("#### 🌾 Futures Margin Call & Roll Horizon Probability")
            fc_c1, fc_c2, fc_c3, fc_c4 = st.columns(4)
            with fc_c1:
                fut_px = st.number_input("Futures Price ($)", value=75.40, step=0.5, key="fc_px_sim")
            with fc_c2:
                fut_mct = st.number_input("Margin Call Trigger Price ($)", value=68.50, step=0.5, key="fc_mct_sim")
            with fc_c3:
                fut_days = st.number_input("Days to Roll / Settlement", min_value=1, value=28, step=1, key="fc_days_sim")
            with fc_c4:
                fut_vol = st.number_input("Annualized Volatility (%)", value=35.0, step=1.0, key="fc_vol_sim") / 100.0

            fc_sim = sim_engine.simulate_futures_margin_risk(
                futures_price=fut_px,
                margin_call_trigger_price=fut_mct,
                days_to_expiry=fut_days,
                volatility=fut_vol
            )

            f1, f2, f3 = st.columns(3)
            f1.metric("Prob Margin Call Breach", f"{fc_sim['prob_margin_call_breach_pct']:.1f}%", fc_sim["risk_level"])
            f2.metric("Margin Headroom Buffer", f"{fc_sim['margin_headroom_pct']:.1f}%", "To Liquidation")
            f3.metric("Risk Classification", fc_sim["risk_level"], "Institutional Gatekeeper")

        # ---------------------------------------------------------------------
        # 4. CRYPTO 24/7 PERPETUALS (LIQUIDATION BREACH PROBABILITY)
        # ---------------------------------------------------------------------
        elif "Crypto" in sim_asset_mode:
            st.markdown("#### ⚡ Continuous 24/7 Liquidation Vulnerability Simulator")
            cr_c1, cr_c2, cr_c3, cr_c4 = st.columns(4)
            with cr_c1:
                cr_sp_in = st.number_input("Perpetual Mark Price ($)", value=65000.0, step=500.0, key="cr_sp_sim")
            with cr_c2:
                cr_lq_in = st.number_input("Liquidation Engine Price ($)", value=float(cr_sp_in * 0.90), step=500.0, key="cr_lq_sim")
            with cr_c3:
                cr_hrs = st.number_input("Window Horizon (Hours)", min_value=1, value=72, step=12, key="cr_hrs_sim")
            with cr_c4:
                cr_v_in = st.number_input("Crypto Volatility (%)", value=65.0, step=5.0, key="cr_vol_sim") / 100.0

            cr_sim = sim_engine.simulate_crypto_perpetual_risk(
                spot_price=cr_sp_in,
                liquidation_price=cr_lq_in,
                volatility=cr_v_in,
                hours_to_evaluate=cr_hrs
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Liquidation Probability", f"{cr_sim['prob_liquidation_pct']:.2f}%", f"{cr_hrs}h Continuous Window")
            c2.metric("Adverse Move Buffer", f"{cr_sim['adverse_buffer_pct']:.1f}%", "Buffer to Engine")
            c3.metric("Cascade Fragility Score", f"{cr_sim['cascade_probability_score']:.1f}/100", cr_sim["status"])
            c4.metric("Status Flag", cr_sim["status"], "Exchange Risk Engine")

        # ---------------------------------------------------------------------
        # 5. MULTI-ASSET PORTFOLIO (MAX DRAWDOWN & HURDLE PROBABILITY)
        # ---------------------------------------------------------------------
        else:
            st.markdown("#### 🛡️ Multi-Asset Portfolio Continuous Drawdown Simulator")
            p_c1, p_c2, p_c3, p_c4 = st.columns(4)
            with p_c1:
                p_cap = st.number_input("Portfolio Capital ($USD)", value=1000000.0, step=1000.0, key="p_cap_sim")
            with p_c2:
                p_vol = st.number_input("Annualized Portfolio Volatility (%)", value=14.0, step=1.0, key="p_vol_sim") / 100.0
            with p_c3:
                p_ret = st.number_input("Expected Annual Return (%)", value=8.5, step=0.5, key="p_ret_sim") / 100.0
            with p_c4:
                p_days = st.number_input("Horizon (Trading Days)", value=252, step=21, key="p_days_sim")

            p_sim = sim_engine.simulate_portfolio_drawdown_probability(
                capital=p_cap,
                annual_vol=p_vol,
                annual_drift=p_ret,
                days_horizon=p_days
            )

            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Prob >5% Drawdown", f"{p_sim['prob_drawdown_5_pct']:.1f}%", "Moderate pullback")
            d2.metric("Prob >10% Drawdown", f"{p_sim['prob_drawdown_10_pct']:.1f}%", "Market correction")
            d3.metric("Prob >15% Drawdown", f"{p_sim['prob_drawdown_15_pct']:.1f}%", "Elevated volatility")
            d4.metric("Prob >20% Drawdown", f"{p_sim['prob_drawdown_20_pct']:.1f}%", "Bear market drawdown")

    # =========================================================================
    # TAB 4: FUTURES & COMMODITY DESK
    # =========================================================================
    with tab_fut:
        st.markdown("### 🌾 Futures & Commodity Desk")
        st.caption("Term structure curve analysis, Contango vs. Backwardation roll yields, and exchange leverage & margin buffer auditing.")

        with st.expander("📐 Futures Term Structure, Cost-of-Carry & Margin Formulas Audit", expanded=False):
            st.markdown(r"""
            #### 🧮 Futures Pricing, Term Structure & Exchange Margin Mathematics
            - **Cost of Carry Model (Continuous Yield & Storage)**:
              $$F(t, T) = S_t \, e^{(r - q + u)(T - t)}$$
              Where $r$ is the risk-free rate, $q$ is the convenience yield (or dividend yield), and $u$ is storage/insurance costs.
            - **Cash-and-Futures Basis**:
              $$\text{Basis}_t = S_t - F_t$$
            - **Annualized Roll Yield (Contango vs. Backwardation)**:
              $$\text{Roll Yield}_{\text{ann}} = \frac{F_{\text{prompt}} - F_{\text{deferred}}}{F_{\text{prompt}}} \times \frac{365}{\Delta t_{\text{days}}}$$
              - If $F_{\text{deferred}} > F_{\text{prompt}}$: **Contango** (negative roll yield / structural drag on long positions).
              - If $F_{\text{prompt}} > F_{\text{deferred}}$: **Backwardation** (positive roll yield / structural carry benefit on long positions).
            - **Total Contract Notional Value**:
              $$\text{Notional} = N_{\text{contracts}} \times F \times M$$
              Where $M$ is the contract multiplier (e.g., 1,000 bbl for CL, 100 oz for GC).
            - **Effective Financial Leverage**:
              $$\text{Leverage} = \frac{\text{Total Notional}}{\text{Account Equity}} = \frac{N_{\text{contracts}} \times F \times M}{\text{Equity}}$$
            - **Exchange Maintenance Margin Call Trigger**:
              $$\text{Trigger Price (Long)} = F - \frac{\text{Account Equity} - \text{Total Maintenance Margin}}{N_{\text{contracts}} \times M}$$
              $$\text{Max Adverse Move (\%)} = \left(\frac{\text{Free Margin Headroom}}{\text{Total Notional}}\right) \times 100\%$$
            """)

        col_fc1, col_fc2 = st.columns([1.1, 1.9])
        with col_fc1:
            st.markdown("#### 📦 Commodity & Curve Input")
            comm_choice = st.selectbox(
                "Commodity Asset Class",
                ["WTI Crude Oil (CL)", "Brent Crude (BZ)", "Gold (GC)", "Silver (SI)", "Copper (HG)", "Natural Gas (NG)"],
                key="fc_comm"
            )
            symbol_map = {"WTI Crude Oil (CL)": "CL", "Brent Crude (BZ)": "BZ", "Gold (GC)": "GC", "Silver (SI)": "SI", "Copper (HG)": "HG", "Natural Gas (NG)": "NG"}
            sym = symbol_map[comm_choice]

            prompt_px = st.number_input("Front Month Price ($)", min_value=0.1, value=75.40, step=0.5, key="fc_px")
            curve_bias = st.radio("Term Structure Posture", ["Contango (Headwind)", "Backwardation (Tailwind)"], horizontal=True, key="fc_bias")

            # Generate synthetic curve based on choice
            if "Contango" in curve_bias:
                f_curve = [
                    {"contract": "M1 (Prompt)", "days_to_expiry": 28, "price": prompt_px},
                    {"contract": "M2 (+1 Mo)", "days_to_expiry": 58, "price": prompt_px * 1.015},
                    {"contract": "M3 (+2 Mo)", "days_to_expiry": 88, "price": prompt_px * 1.028},
                    {"contract": "M6 (+5 Mo)", "days_to_expiry": 178, "price": prompt_px * 1.055},
                    {"contract": "M12 (+11 Mo)", "days_to_expiry": 358, "price": prompt_px * 1.090}
                ]
            else:
                f_curve = [
                    {"contract": "M1 (Prompt)", "days_to_expiry": 28, "price": prompt_px},
                    {"contract": "M2 (+1 Mo)", "days_to_expiry": 58, "price": prompt_px * 0.985},
                    {"contract": "M3 (+2 Mo)", "days_to_expiry": 88, "price": prompt_px * 0.970},
                    {"contract": "M6 (+5 Mo)", "days_to_expiry": 178, "price": prompt_px * 0.945},
                    {"contract": "M12 (+11 Mo)", "days_to_expiry": 358, "price": prompt_px * 0.910}
                ]

            fut_res = orchestrator.futures_desk.evaluate_term_structure(
                symbol=sym,
                commodity_name=comm_choice,
                curve=f_curve
            )

        with col_fc2:
            st.markdown("#### 📈 Term Structure Curve")
            ts = fut_res["term_structure"]
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(
                x=[c["days_to_expiry"] for c in f_curve],
                y=[c["price"] for c in f_curve],
                mode="lines+markers+text",
                text=[c["contract"] for c in f_curve],
                textposition="top center",
                line=dict(color="#F59E0B", width=3),
                marker=dict(size=8, color="#F8FAFC")
            ))
            fig_curve.update_layout(
                title=f"{comm_choice} Term Structure: {ts['curve_regime']}",
                xaxis_title="Days to Expiration",
                yaxis_title="Futures Contract Price ($)",
                template="plotly_dark",
                height=300,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_curve, use_container_width=True)

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Regime", "Contango" if ts["is_contango"] else "Backwardation", ts["curve_regime"])
            k2.metric("Front-to-Next Roll Yield", f"{ts['front_to_deferred_roll_yield_annual_pct']:+.2f}%/yr", "Annualized")
            k3.metric("Curve Slope", f"{ts['curve_slope_annual_pct']:+.2f}%", "12M Spread")
            k4.metric("Tactical Bias", fut_res["tactical_bias"], "Roll Harvest")

        # Margin and Leverage Stress Tester
        st.divider()
        st.markdown("#### ⚡ Exchange Initial / Maintenance Margin Stress Tester")
        col_mg1, col_mg2, col_mg3, col_mg4, col_mg5 = st.columns(5)
        with col_mg1:
            multiplier = st.number_input("Multiplier", value=1000.0, step=100.0, key="fc_mult")
        with col_mg2:
            n_contracts = st.number_input("Contracts", min_value=1, value=15, step=1, key="fc_cnt")
        with col_mg3:
            init_margin = st.number_input("Initial Margin / Ctr ($)", value=6500.0, step=500.0, key="fc_im")
        with col_mg4:
            maint_margin = st.number_input("Maint. Margin / Ctr ($)", value=5000.0, step=500.0, key="fc_mm")
        with col_mg5:
            acct_eq = st.number_input("Account Equity ($)", value=150000.0, step=10000.0, key="fc_eq")

        margin_res = orchestrator.futures_desk.assess_margin_and_leverage(
            symbol=sym,
            futures_price=prompt_px,
            contract_multiplier=multiplier,
            num_contracts=n_contracts,
            initial_margin_per_contract=init_margin,
            maintenance_margin_per_contract=maint_margin,
            account_equity=acct_eq
        )

        ma = margin_res["margin_audit"]
        st.caption(f"Contract Exposure: **{n_contracts:,} contracts** | Multiplier: **{multiplier:,.0f}** | Total Notional: **${ma['total_notional']:,.2f}** | Initial Margin: **${ma['total_initial_margin']:,.2f}** | Maintenance Margin: **${ma['total_maintenance_margin']:,.2f}**")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Effective Leverage", f"{ma['effective_leverage']:.1f}x", "Institutional Limit: 10x")
        m2.metric("Margin Utilization", f"{ma['margin_utilization_pct']:.1f}%", ma["risk_status"])
        m3.metric("Free Headroom", f"${ma['free_margin_headroom']:,.0f}", "Buffer")
        m4.metric("Margin Call Price", f"${ma['margin_call_trigger_price']:,.2f}", f"-{ma['max_adverse_move_pct']:.1f}% adverse")
        m5.metric("Audit Verdict", margin_res["verdict"], "Risk Cap Checked")

        # ---------------------------------------------------------------------
        # LIVE FUTURES DEAL EXECUTION DESK ($1,000,000 SIMULATION CAPITAL)
        # ---------------------------------------------------------------------
        st.markdown("##### ⚡ Execute Futures Contract into Portfolio ($1,000,000 Capital Balance)")
        pe_fut = get_paper_trading_engine()
        fut_p = pe_fut.load_portfolio()
        fut_cash = float(fut_p.get("cash_balance", INITIAL_PORTFOLIO_CASH))

        fc_e1, fc_e2, fc_e3 = st.columns([1, 1, 1.5])
        with fc_e1:
            fut_side = st.radio("Side", ["BUY (Long)", "SELL (Short)"], horizontal=True, key=f"fut_side_{sym}")
        with fc_e2:
            fut_trade_qty = st.number_input("Contracts to Trade", min_value=1, max_value=100, value=1, step=1, key=f"fut_qty_{sym}")
        with fc_e3:
            clean_f_side = "BUY" if "BUY" in fut_side else "SELL"
            req_margin = fut_trade_qty * init_margin
            active_venue_fut = st.session_state.get("active_routing_venue", "CME_GLOBEX")
            active_mode_fut = st.session_state.get("active_execution_mode", "SIMULATION_PAPER")
            tca_fut = ExecutionCostModel.calculate_execution_costs(
                asset_class="Futures",
                side=clean_f_side,
                quantity=float(fut_trade_qty),
                price=float(prompt_px)
            )
            st.caption(f"Required Initial Margin: **${req_margin:,.2f} USD** | Venue: <b style='color:#38BDF8;'>{active_venue_fut}</b> | Est TCA Friction: **${tca_fut['total_friction_usd']:,.2f} USD**")
            if st.button("🟢 EXECUTE FUTURES ORDER ($)", type="primary", use_container_width=True, key=f"btn_fut_exec_{sym}"):
                f_ok, f_msg, f_pos = pe_fut.execute_trade(
                    symbol=f"{sym}=F",
                    asset_class="Futures",
                    side=clean_f_side,
                    quantity=float(fut_trade_qty),
                    price=float(prompt_px),
                    strategy_type=f"Futures {clean_f_side}",
                    multiplier=float(multiplier),
                    margin_per_unit=float(init_margin),
                    routing_venue=active_venue_fut,
                    execution_mode=active_mode_fut,
                    notes=f"{comm_choice} @ ${prompt_px:,.2f}"
                )
                if f_ok:
                    st.success(f_msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f_msg)

    # =========================================================================
    # TAB 4: FIXED INCOME MACRO AGENT
    # =========================================================================
    with tab_fi:
        st.markdown("### 📈 Fixed Income Macro Agent")
        st.caption("Sovereign yield curve inversion tracking, Macaulay & Modified duration, Convexity, DV01 ($ per bp), and interest rate shocks.")

        with st.expander("📐 Fixed Income Bond Pricing, Duration, Convexity & DV01 Formulas Audit", expanded=False):
            st.markdown(r"""
            #### 🧮 Bond Valuation, Interest Rate Sensitivities & Yield Curve Mathematics
            - **Bond Dirty / Full Price**:
              $$P = \sum_{t=1}^n \frac{C}{(1 + y)^t} + \frac{M}{(1 + y)^n}$$
              Where $C$ is coupon payment, $y$ is yield-to-maturity, $M$ is par value, and $n$ is periods to maturity.
            - **Macaulay Duration (Weighted Average Maturity)**:
              $$D_{\text{mac}} = \frac{1}{P} \sum_{t=1}^n \frac{t \cdot C_t}{(1 + y)^t} \quad \text{(years)}$$
            - **Modified Duration (Direct Rate Sensitivity)**:
              $$D_{\text{mod}} = \frac{D_{\text{mac}}}{1 + y} = -\frac{1}{P} \frac{\partial P}{\partial y}$$
            - **Bond Convexity (Curvature Sensitivity)**:
              $$C = \frac{1}{P (1 + y)^2} \sum_{t=1}^n \frac{t(t + 1) C_t}{(1 + y)^t} = \frac{1}{P} \frac{\partial^2 P}{\partial y^2}$$
            - **Dollar Value of a Basis Point (DV01)**:
              $$\text{DV01} = D_{\text{mod}} \times P \times 0.0001 = -\frac{\Delta P}{\Delta y \text{ (in bps)}}$$
              $$\text{DV01 per \$1,000,000 Par} = \text{DV01} \times \left(\frac{1,000,000}{\text{Face Value}}\right)$$
            - **Second-Order Taylor Series Price Shock Approximation**:
              $$\frac{\Delta P}{P} \approx - D_{\text{mod}} \Delta y + \frac{1}{2} C (\Delta y)^2$$
            - **Yield Curve Slopes & Inversion**:
              $$\text{Spread}_{2\text{Y}-10\text{Y}} = (y_{10\text{Y}} - y_{2\text{Y}}) \times 100 \text{ bps}$$
              $$\text{Spread}_{3\text{M}-10\text{Y}} = (y_{10\text{Y}} - y_{3\text{M}}) \times 100 \text{ bps}$$
              Negative spreads indicate yield curve inversion and historically elevated recession probability.
            """)

        col_fi1, col_fi2 = st.columns([1.1, 1.9])
        with col_fi1:
            st.markdown("#### 🏛️ US Treasury Yield Curve Points")
            y3m = st.number_input("3-Month Bill Yield (%)", value=4.85, step=0.05, key="fi_3m")
            y2 = st.number_input("2-Year Note Yield (%)", value=4.05, step=0.05, key="fi_2y")
            y5 = st.number_input("5-Year Note Yield (%)", value=3.90, step=0.05, key="fi_5y")
            y10 = st.number_input("10-Year Benchmark (%)", value=4.20, step=0.05, key="fi_10y")
            y30 = st.number_input("30-Year Bond Yield (%)", value=4.50, step=0.05, key="fi_30y")

            rates_input = {"3M": y3m, "2Y": y2, "5Y": y5, "10Y": y10, "30Y": y30}
            macro_res = orchestrator.macro_desk.evaluate_yield_curve_macro(rates_input)

        with col_fi2:
            st.markdown("#### 📊 Yield Curve Structure & Slope")
            y_pts = ["3M", "2Y", "5Y", "10Y", "30Y"]
            y_vals = [rates_input[p] for p in y_pts]

            fig_yc = go.Figure()
            fig_yc.add_trace(go.Scatter(
                x=y_pts, y=y_vals,
                mode="lines+markers",
                line=dict(color="#10B981", width=3),
                marker=dict(size=8, color="#F8FAFC")
            ))
            fig_yc.update_layout(
                title=f"US Treasury Curve: {macro_res['yield_curve_analysis']['curve_regime']}",
                xaxis_title="Tenor",
                yaxis_title="Yield (%)",
                template="plotly_dark",
                height=280,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_yc, use_container_width=True)

            yca = macro_res["yield_curve_analysis"]
            yc1, yc2, yc3, yc4 = st.columns(4)
            yc1.metric("2Y-10Y Spread", f"{yca['spread_2y_10y_bps']:+.1f} bps", "Recession Signal" if yca["spread_2y_10y_bps"] < 0 else "Normal")
            yc2.metric("3M-10Y Spread", f"{yca['spread_3m_10y_bps']:+.1f} bps", "Money Market Curve")
            yc3.metric("Curve Regime", yca["curve_regime"].split()[0], yca["curve_regime"])
            yc4.metric("Recession Risk", yca["recession_probability_indicator"], "Macro leading ind.")

        # Bond Duration & Interest Rate Shock Matrix
        st.divider()
        st.markdown("#### ⚡ Sovereign & Corporate Bond Sensitivity (DV01 & Convexity)")
        b_c1, b_c2, b_c3, b_c4 = st.columns(4)
        with b_c1:
            b_face = st.number_input("Face Value ($)", value=1000.0, step=100.0, key="fi_face")
        with b_c2:
            b_coupon = st.number_input("Coupon Rate (%)", value=4.5, step=0.25, key="fi_cp") / 100.0
        with b_c3:
            b_ytm = st.number_input("Yield-to-Maturity (%)", value=4.2, step=0.1, key="fi_ytm") / 100.0
        with b_c4:
            b_mat = st.number_input("Years to Maturity", min_value=1.0, value=10.0, step=1.0, key="fi_mat")

        bond_res = orchestrator.macro_desk.analyze_bond(
            security_name="Benchmark 10Y Sovereign Note",
            face_value=b_face,
            coupon_rate_annual=b_coupon,
            yield_to_maturity_annual=b_ytm,
            years_to_maturity=b_mat
        )

        bm = bond_res["metrics"]
        bm1, bm2, bm3, bm4 = st.columns(4)
        bm1.metric("Clean / Dirty Price", f"${bm['price']:,.2f}", f"Par ${b_face:,.0f}")
        bm2.metric("Modified Duration", f"{bm['modified_duration']:.2f} yrs", f"Mac: {bm['macaulay_duration_years']:.2f} yrs")
        bm3.metric("Convexity", f"{bm['convexity']:.2f}", "Second-order buffer")
        bm4.metric("DV01 / Million Par", f"${bm['dv01_per_million_par']:,.2f}", "$ loss per +1 bp")

        # Rate Shock Matrix Visualizer
        shocks = bm["rate_shocks"]
        fig_shocks = go.Figure()
        fig_shocks.add_trace(go.Bar(
            x=[k for k in shocks.keys()],
            y=[shocks[k]["pct_change"] for k in shocks.keys()],
            marker_color=["#10B981" if shocks[k]["pct_change"] > 0 else "#F43F5E" for k in shocks.keys()]
        ))
        fig_shocks.update_layout(
            title="Bond Price Sensitivity under Parallel Yield Curve Shifts (Duration + Convexity)",
            xaxis_title="Yield Shift (Basis Points)",
            yaxis_title="Projected Capital Return (%)",
            template="plotly_dark",
            height=280,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_shocks, use_container_width=True)

    # =========================================================================
    # TAB 5: CRYPTO & 24/7 DERIVATIVES AGENT
    # =========================================================================
    with tab_crypto:
        st.markdown("### ⚡ Crypto & 24/7 Derivatives Agent")
        st.caption("Continuous 24/7 market microstructure, perpetual swap funding rates, cash-and-carry basis arbitrage, and liquidation cascade modeling.")

        with st.expander("📐 Perpetual Swap Funding, Cash-and-Carry Basis & Liquidation Formulas Audit", expanded=False):
            st.markdown(r"""
            #### 🧮 24/7 Crypto Derivatives, Funding Carry & Liquidation Microstructure
            - **Perpetual Swap Premium Index**:
              $$\mathcal{P} = \frac{\text{Mark Price} - \text{Index Spot}}{\text{Index Spot}} \times 10{,}000 \text{ (in basis points)}$$
            - **Annualized Funding Carry**:
              $$\text{Simple Annualized Rate} = F_{8h} \times 3 \times 365 = F_{8h} \times 1{,}095$$
              $$\text{Compound APY} = \left(1 + \frac{F_{8h}}{100}\right)^{1095} - 1$$
            - **Cash-and-Carry Basis Arbitrage**:
              $$\text{Gross Basis} = F_{\text{dated}} - S_{\text{spot}}$$
              $$\text{Gross Annualized APY} = \left(\frac{F_{\text{dated}} - S_{\text{spot}}}{S_{\text{spot}}}\right) \times \frac{365}{\text{DTE}} \times 100\%$$
              $$\text{Net Annualized APY} = \left(\frac{F_{\text{dated}} - S_{\text{spot}} - \text{Execution Costs}}{S_{\text{spot}}}\right) \times \frac{365}{\text{DTE}} \times 100\%$$
            - **Exchange Liquidation Engine Trigger Price**:
              - **Long Position**:
                $$P_{\text{liq}}^{\text{long}} = P_{\text{entry}} \times \left(1 - \frac{1}{\text{Leverage}} + \text{MMR}\right)$$
              - **Short Position**:
                $$P_{\text{liq}}^{\text{short}} = P_{\text{entry}} \times \left(1 + \frac{1}{\text{Leverage}} - \text{MMR}\right)$$
              Where $\text{MMR}$ is the maintenance margin requirement (typically $0.5\% = 0.005$ on BTC).
            - **Liquidation Cascade Vulnerability Score**:
              $$\text{Score} = \min\left(100, \, \left(\frac{\text{Open Interest}}{\text{24h Volume}} \times 40\right) + \left(\frac{|F_{8h}|}{0.05\%} \times 30\right) + \text{Leverage Penalty}\right)$$
            """)

        col_cr1, col_cr2 = st.columns([1.1, 1.9])
        with col_cr1:
            st.markdown("#### 🪙 Perpetual Swap Microstructure")
            cr_sym = st.selectbox("Asset Contract", ["BTC-PERP", "ETH-PERP", "SOL-PERP"], key="cr_sym")
            cr_spot = st.number_input("Spot Index ($)", min_value=1.0, value=65000.0, step=500.0, key="cr_sp")
            cr_mark = st.number_input("Perp Mark Price ($)", min_value=1.0, value=65080.0, step=500.0, key="cr_mk")
            cr_f8 = st.number_input("Current 8h Funding Rate (%)", value=0.012, step=0.005, format="%.4f", key="cr_f8")
            cr_oi = st.number_input("Open Interest ($USD)", value=1_500_000_000.0, step=100_000_000.0, key="cr_oi")
            cr_vol = st.number_input("24h Volume ($USD)", value=5_000_000_000.0, step=500_000_000.0, key="cr_vl")
            st.caption(f"Spot: **${cr_spot:,.2f}** | Mark: **${cr_mark:,.2f}** | OI: **${cr_oi:,.0f}** | 24h Vol: **${cr_vol:,.0f}**")

            crypto_res = orchestrator.crypto_desk.analyze_perpetual_funding(
                symbol=cr_sym,
                spot_price=cr_spot,
                mark_price=cr_mark,
                funding_rate_8h_pct=cr_f8,
                open_interest_usd=cr_oi,
                daily_volume_usd=cr_vol
            )

        with col_cr2:
            st.markdown("#### 📊 Funding Carry & Liquidation Cascade Gauge")
            fa = crypto_res["funding_analysis"]
            cr1, cr2, cr3, cr4 = st.columns(4)
            cr1.metric("Simple Annualized", f"{fa['simple_annualized_pct']:+.2f}%", "Annual Carry")
            cr2.metric("Compound APY", f"{fa['compound_apy_pct']:+.2f}%", "Reinvested")
            cr3.metric("Premium Index", f"{fa['premium_index_bps']:+.1f} bps", fa["carry_direction"].split()[0])
            cr4.metric("Cascade Risk", f"{fa['liquidation_cascade_risk_score']:.0f}/100", fa["cascade_alert"])

            # Liquidation cascade gauge
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=fa["liquidation_cascade_risk_score"],
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': f"Liquidation Cascade Vulnerability ({cr_sym})"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#F43F5E" if fa["liquidation_cascade_risk_score"] > 70 else "#F59E0B" if fa["liquidation_cascade_risk_score"] > 40 else "#10B981"},
                    'steps': [
                        {'range': [0, 40], 'color': "rgba(16,185,129,0.15)"},
                        {'range': [40, 70], 'color': "rgba(245,158,11,0.15)"},
                        {'range': [70, 100], 'color': "rgba(244,63,94,0.25)"}
                    ]
                }
            ))
            fig_gauge.update_layout(template="plotly_dark", height=240, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

        # Cash and Carry Basis & Liquidation Distance
        st.divider()
        col_ar1, col_ar2 = st.columns(2)
        with col_ar1:
            st.markdown("#### ⚡ Cash-and-Carry Basis Arbitrage")
            cr_fut_px = st.number_input("Dated Quarterly Futures Price ($)", value=66800.0, step=100.0, key="cr_fut_px")
            cr_days = st.number_input("Days to Futures Expiration", min_value=1, value=90, step=1, key="cr_days")
            basis_res = orchestrator.crypto_desk.evaluate_basis_arbitrage(
                symbol=cr_sym,
                spot_price=cr_spot,
                dated_futures_price=cr_fut_px,
                days_to_expiry=cr_days
            )
            ba = basis_res["basis_arbitrage"]
            b1, b2 = st.columns(2)
            b1.metric("Gross Basis APY", f"{ba['gross_annualized_apy_pct']:+.2f}%", f"+${ba['gross_basis']:,.2f}")
            b2.metric("Net APY (After Fees)", f"{ba['net_annualized_apy_pct']:+.2f}%", "Arbitrage Viable" if ba["arbitrage_viable"] else "Unprofitable")

        with col_ar2:
            st.markdown("#### 🚨 24/7 Liquidation Buffer Distance")
            cr_lev = st.slider("Position Leverage Ratio", 1.0, 50.0, 10.0, 1.0, key="cr_lev_sl")
            liq_res = orchestrator.crypto_desk.evaluate_liquidation_buffer(
                symbol=cr_sym,
                entry_price=cr_spot,
                leverage=cr_lev,
                position_side="long"
            )
            lm = liq_res["liquidation_metrics"]
            l1, l2 = st.columns(2)
            l1.metric("Liquidation Price", f"${lm['liquidation_price']:,.2f}", f"-{lm['adverse_buffer_pct']:.1f}% Buffer")
            l2.metric("Danger Status", lm["danger_level"], liq_res["verdict"])

        # ---------------------------------------------------------------------
        # LIVE CRYPTO DEAL EXECUTION DESK ($1,000,000 SIMULATION CAPITAL)
        # ---------------------------------------------------------------------
        st.divider()
        st.markdown("#### ⚡ Execute Crypto Perpetual Deal into Portfolio ($1,000,000 Capital Balance)")
        pe_cr = get_paper_trading_engine()
        cr_p = pe_cr.load_portfolio()
        cr_cash = float(cr_p.get("cash_balance", INITIAL_PORTFOLIO_CASH))

        cr_e1, cr_e2, cr_e3 = st.columns([1, 1, 1.5])
        with cr_e1:
            cr_side = st.radio("Side", ["BUY (Long)", "SELL (Short)"], horizontal=True, key=f"cr_side_{cr_sym}")
        with cr_e2:
            cr_qty = st.number_input("Position Size (Coins)", min_value=0.01, max_value=100.0, value=0.50, step=0.05, format="%.2f", key=f"cr_qty_{cr_sym}")
        with cr_e3:
            clean_cr_side = "BUY" if "BUY" in cr_side else "SELL"
            req_cr_margin = (cr_qty * cr_spot) / cr_lev
            active_venue_cr = st.session_state.get("active_routing_venue", "DARK_POOL_CROSS")
            active_mode_cr = st.session_state.get("active_execution_mode", "SIMULATION_PAPER")
            tca_cr = ExecutionCostModel.calculate_execution_costs(
                asset_class="Crypto",
                side=clean_cr_side,
                quantity=float(cr_qty),
                price=float(cr_spot)
            )
            st.caption(f"Required Margin ({cr_lev:.0f}x): **${req_cr_margin:,.2f} USD** | Venue: <b style='color:#38BDF8;'>{active_venue_cr}</b> | Est TCA Friction: **${tca_cr['total_friction_usd']:,.2f} USD**")
            if st.button("🟢 EXECUTE PERPETUAL SWAP ($)", type="primary", use_container_width=True, key=f"btn_cr_exec_{cr_sym}"):
                c_ok, c_msg, c_pos = pe_cr.execute_trade(
                    symbol=cr_sym.replace("-PERP", "-USD"),
                    asset_class="Crypto",
                    side=clean_cr_side,
                    quantity=float(cr_qty),
                    price=float(cr_spot),
                    strategy_type=f"Crypto Perpetual ({cr_lev:.0f}x)",
                    multiplier=1.0,
                    margin_per_unit=float(cr_spot / cr_lev),
                    routing_venue=active_venue_cr,
                    execution_mode=active_mode_cr,
                    notes=f"{cr_sym} @ ${cr_spot:,.2f} ({cr_lev:.0f}x Leverage)"
                )
                if c_ok:
                    st.success(c_msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(c_msg)

    # =========================================================================
    # TAB 6: CROSS-ASSET RISK OFFICER & RED FLAGS
    # =========================================================================
    with tab_risk:
        st.markdown("### 🛡️ Cross-Asset Risk Officer & Red Flags Registry")
        st.caption("Parametric & Historical Value-at-Risk (VaR), Expected Shortfall (CVaR), Correlation Heatmaps, Crisis Stress Matrix, and Institutional Red Flags.")

        with st.expander("📐 Cross-Asset Portfolio Risk, VaR, CVaR & Stress Testing Formulas Audit", expanded=False):
            st.markdown(r"""
            #### 🧮 Portfolio Risk Aggregation, Extreme Tail Risk & Capital Guardrails
            - **Cross-Asset Covariance Matrix Decomposition**:
              $$\boldsymbol{\Sigma} = \mathbf{D} \, \mathbf{R} \, \mathbf{D}$$
              Where $\mathbf{D} = \text{diag}(\sigma_1, \sigma_2, \dots, \sigma_n)$ is the diagonal volatility matrix and $\mathbf{R}$ is the cross-asset correlation matrix ($R_{ij} = \rho_{ij}$).
            - **Portfolio Return Variance & Standard Deviation**:
              $$\sigma_p^2 = \mathbf{w}^T \boldsymbol{\Sigma} \mathbf{w} = \sum_{i=1}^n \sum_{j=1}^n w_i w_j \sigma_i \sigma_j \rho_{ij}$$
              $$\sigma_p = \sqrt{\mathbf{w}^T \boldsymbol{\Sigma} \mathbf{w}}$$
            - **Parametric 1-Day Value-at-Risk (VaR at confidence level $\alpha$)**:
              $$\text{VaR}_\alpha = z_\alpha \cdot \sigma_p \cdot \sqrt{\frac{1}{252}} \cdot W_{\text{portfolio}}$$
              Where $z_{0.95} \approx 1.6449$, $z_{0.99} \approx 2.3263$, and $W_{\text{portfolio}}$ is total fund capital.
            - **Parametric Expected Shortfall / Conditional VaR (CVaR)**:
              $$\text{CVaR}_\alpha = \mathbb{E}[L \mid L > \text{VaR}_\alpha] = \frac{\phi(z_\alpha)}{1 - \alpha} \cdot \sigma_p \cdot \sqrt{\frac{1}{252}} \cdot W_{\text{portfolio}}$$
              Where $\phi(z)$ is the standard Gaussian probability density function.
            - **Black-Swan Crisis Scenario Factor Shock**:
              $$\Delta W_{\text{crisis}} = \sum_{i=1}^n w_i \cdot W_{\text{portfolio}} \cdot \Delta r_{i, \text{crisis}}$$
            - **Institutional Risk Appetite Bounds**:
              - Maximum single asset concentration: $w_i \le 40\%$
              - Maximum daily 99% VaR: $\text{VaR}_{99\%} \le 4.5\%$ of fund capital
              - Maximum gross futures leverage: $\text{Gross Leverage} \le 10\times$
              - Hard Gatekeeper Veto: Any active **CRITICAL** red flag triggers immediate trading suspension.
            """)

        # Correlation Matrix Heatmap
        st.markdown("#### 🌐 Cross-Asset Correlation Matrix")
        assets = ["Equities", "Fixed Income", "Commodities", "Crypto", "Options Overlay"]
        corr_data = np.array([
            [1.00, -0.15,  0.35,  0.45, -0.40],
            [-0.15,  1.00, -0.10, -0.05,  0.10],
            [0.35, -0.10,  1.00,  0.25, -0.20],
            [0.45, -0.05,  0.25,  1.00, -0.30],
            [-0.40,  0.10, -0.20, -0.30,  1.00]
        ])

        fig_corr = px.imshow(
            corr_data,
            x=assets,
            y=assets,
            color_continuous_scale="RdBu_r",
            zmin=-1.0,
            zmax=1.0,
            text_auto=".2f",
            title="Institutional Cross-Asset Correlation Matrix (Normal vs Stress Breakdown)"
        )
        fig_corr.update_layout(template="plotly_dark", height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_corr, use_container_width=True)

        # Historical Black-Swan Crisis Stress Matrix
        st.divider()
        st.markdown("#### 🌪️ Historical Crisis Stress Testing Simulator")
        st.caption("Simulates portfolio-wide performance across benchmark historical financial market liquidity crises.")

        default_stress_alloc = {
            "equities": 4_000_000.0,
            "fixed_income": 3_000_000.0,
            "commodities": 1_500_000.0,
            "crypto": 1_000_000.0,
            "options_overlay": 500_000.0
        }
        stress_eval = orchestrator.risk_officer.stress_test_portfolio(default_stress_alloc)
        scenarios = stress_eval["stress_results"]["scenarios"]

        s_names = [s["scenario_name"] for s in scenarios]
        s_dd = [s["projected_drawdown_pct"] for s in scenarios]
        s_pnl = [s["projected_pnl_usd"] for s in scenarios]

        fig_stress = go.Figure()
        fig_stress.add_trace(go.Bar(
            x=s_names,
            y=s_dd,
            marker_color=["#F43F5E" if dd < -20.0 else "#F59E0B" for dd in s_dd],
            text=[f"{dd:.1f}% (${abs(pnl)/1000:,.0f}k)" for dd, pnl in zip(s_dd, s_pnl)],
            textposition="inside"
        ))
        fig_stress.update_layout(
            title="Projected Portfolio Drawdown under Historical Black-Swan Events ($10M Baseline)",
            xaxis_title="Historical Crisis Scenario",
            yaxis_title="Projected Total Portfolio Drawdown (%)",
            template="plotly_dark",
            height=320,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_stress, use_container_width=True)

        # Master Institutional Red Flags Directory
        st.divider()
        st.markdown("#### 🚨 Master Institutional Red Flags Directory & Operational Matrix")
        st.caption("Comprehensive registry of all financial, model, operational, and counterparty red flags tracked across Meridian.")

        red_flags_catalog = [
            ("Gamma Cliff Acceleration", "CRITICAL", "Options Greek Strategist", "Near-expiry options (<7 DTE) exhibit accelerating non-linear gamma acceleration, exposing delta-hedged portfolios to severe gap-risk losses."),
            ("Short Gamma Volatility Spike", "CRITICAL", "Options Greek Strategist", "Net negative gamma across options positions creates parabolic downside losses during volatility expansions and flash crashes."),
            ("Hyper-Leverage Exposure (>10x)", "CRITICAL", "Futures & Commodity Desk", "Position notional-to-equity ratio exceeds institutional safety limits, causing rapid margin depletion under standard daily fluctuations."),
            ("Margin Depletion Imminent (>80%)", "CRITICAL", "Futures & Commodity Desk", "Exchange maintenance margin utilization exceeds 80%, leaving zero cushion for intraday mark-to-market swings."),
            ("Severe Contango Roll Drag (>10%/yr)", "HIGH", "Futures & Commodity Desk", "Upward-sloping commodity futures curves cause passive long positions to systematically bleed capital on contract roll-overs."),
            ("Deep Yield Curve Inversion (-50 bps)", "CRITICAL", "Fixed Income Macro Agent", "2Y-10Y and 3M-10Y curve inversions reflect aggressive monetary tightening and historically herald recessionary credit contraction."),
            ("Ultra-Long Duration Mismatch (>12 yrs)", "HIGH", "Fixed Income Macro Agent", "Elevated modified duration creates severe portfolio vulnerability to upward rate shocks (+100 bps = >12% capital loss)."),
            ("Negative Convexity Mortgages/Calls", "HIGH", "Fixed Income Macro Agent", "Asymmetric return profile cap price upside during rate rallies while accelerating capital losses during rate spikes."),
            ("Reckless 24/7 Crypto Leverage (>20x)", "CRITICAL", "Crypto & 24/7 Derivatives", "Extreme leverage on volatile continuous assets guarantees eventual automated liquidation during routine flash wicks."),
            ("Flash Liquidation Proximity (<8% buffer)", "CRITICAL", "Crypto & 24/7 Derivatives", "Mark price is within 8% of the exchange liquidation engine trigger price, risking forced market sell-off."),
            ("Perpetual Funding Rate Dislocation (>40% APY)", "HIGH", "Crypto & 24/7 Derivatives", "Massive speculative skew forces long holders to pay exorbitant carry, eroding profit margins rapidly."),
            ("Excessive 1-Day 99% VaR (>4.5%)", "CRITICAL", "Cross-Asset Risk Officer", "Statistically expected daily capital loss at the 99% confidence level exceeds institutional risk appetite guidelines."),
            ("Single-Asset Concentration Risk (>40%)", "HIGH", "Cross-Asset Risk Officer", "Excessive capital weighting in a single risk factor negates cross-asset diversification benefits during market crises.")
        ]

        rf_col1, rf_col2 = st.columns(2)
        for idx, (title, severity, desk, desc) in enumerate(red_flags_catalog):
            col = rf_col1 if idx % 2 == 0 else rf_col2
            b_color = "#F43F5E" if severity == "CRITICAL" else "#F59E0B"
            with col:
                st.markdown(f"""
                <div style="background:rgba(18,24,36,0.7); border:1px solid #1E2638; border-left:3px solid {b_color}; border-radius:6px; padding:12px 14px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#F8FAFC; font-size:0.86rem;">{title}</span>
                        <span style="background:rgba(255,255,255,0.08); color:{b_color}; font-size:0.70rem; font-weight:700; padding:2px 7px; border-radius:4px;">{severity}</span>
                    </div>
                    <div style="font-size:0.75rem; color:#38BDF8; margin-top:2px; font-family:monospace;">{desk}</div>
                    <div style="font-size:0.78rem; color:#94A3B8; margin-top:6px;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 8: WALK-FORWARD BACKTESTER & AUTOMATED STRATEGY ALGO ENGINE
    # =========================================================================
    with tab_bt:
        st.markdown("### 📊 Institutional Walk-Forward Multi-Asset Backtester & Automated Strategy Algo Engine")
        st.caption("Rolling In-Sample/Out-of-Sample cross-validation with zero lookahead bias, non-linear Kyle/Almgren-Chriss TCA friction, Cornish-Fisher VaR trailing stops, Half-Kelly capital sizing, and autonomous positive-expectancy scanner.")

        bt_sub1, bt_sub2 = st.tabs([
            "📈 Walk-Forward Multi-Asset Backtester",
            "🤖 Autonomous Strategy Algo Scanner & Committee Dispatch"
        ])

        with bt_sub1:
            st.markdown("#### 🔬 Rolling Walk-Forward Strategy Simulation")
            st.caption("Evaluate strategy robustness across out-of-sample market regimes with realistic market impact and exchange fee friction.")

            # Controls
            c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.2, 1.2])
            with c1:
                strat_choice = st.selectbox(
                    "Algorithmic Strategy Architecture",
                    [
                        "EquityMomentumVolFilter",
                        "OptionsCreditSpreadCarry",
                        "MeanVarianceQP"
                    ],
                    index=0,
                    help="EquityMomentumVolFilter: Trend + Cornish-Fisher VaR filter. OptionsCreditSpreadCarry: OTM Put spreads with POP_CF hurdle. MeanVarianceQP: Rolling Markowitz QP."
                )
            with c2:
                tickers_input = st.text_input(
                    "Portfolio Tickers (comma-separated)",
                    value="AAPL, MSFT, NVDA, SPY",
                    help="Multi-asset basket to simulate."
                )
            with c3:
                tr_window = st.slider("Train Window (Days)", min_value=60, max_value=252, value=180, step=30)
                te_window = st.slider("Test Window (Days)", min_value=20, max_value=120, value=60, step=10)
            with c4:
                init_cap = st.number_input("Initial Capital ($ USD)", min_value=1000.0, max_value=10000000.0, value=1000000.0, step=50000.0)
                bench_sym = st.selectbox("Benchmark", ["SPY", "QQQ"], index=0)

            run_bt_clicked = st.button("🚀 Run Institutional Walk-Forward Backtest", use_container_width=True, type="primary")

            if run_bt_clicked:
                syms = [s.strip().upper() for s in tickers_input.split(",") if s.strip()]
                if not syms:
                    syms = ["AAPL", "MSFT", "SPY"]
                with st.spinner("Executing walk-forward cross-validation folds and non-linear TCA simulation..."):
                    sandbox = BacktestSandbox()
                    bt_res = sandbox.run_walk_forward_backtest(
                        tickers=syms,
                        strategy=strat_choice,
                        benchmark=bench_sym,
                        train_window=int(tr_window),
                        test_window=int(te_window),
                        initial_capital=float(init_cap)
                    )
                    st.session_state["wf_backtest_res"] = bt_res

            res = st.session_state.get("wf_backtest_res")
            if res:
                m = res.get("metrics", {})
                wfe = res.get("walk_forward_efficiency", {})

                # Metric Cards
                st.divider()
                st.markdown("##### 📊 Institutional Performance Summary")
                m_c1, m_c2, m_c3, m_c4, m_c5 = st.columns(5)
                with m_c1:
                    st.metric("Total Return", f"{m.get('total_return_pct', 0.0):+.2f}%", delta=f"{m.get('alpha_pct', 0.0):+.2f}% Alpha")
                with m_c2:
                    st.metric("Benchmark (SPY)", f"{m.get('benchmark_return_pct', 0.0):+.2f}%")
                with m_c3:
                    st.metric("Sharpe Ratio (Rf=4.25%)", f"{m.get('sharpe_ratio', 0.0):.2f}")
                with m_c4:
                    st.metric("Sortino Ratio", f"{m.get('sortino_ratio', 0.0):.2f}")
                with m_c5:
                    st.metric("Calmar Ratio", f"{m.get('calmar_ratio', 0.0):.2f}")

                m_c6, m_c7, m_c8, m_c9, m_c10 = st.columns(5)
                with m_c6:
                    st.metric("Max Drawdown", f"{m.get('max_drawdown_pct', 0.0):.2f}%")
                with m_c7:
                    st.metric("Max DD Duration", f"{m.get('max_drawdown_duration_days', 0)} days")
                with m_c8:
                    st.metric("Win Rate %", f"{m.get('win_rate_pct', 0.0):.1f}%", f"{m.get('winning_trades', 0)}/{m.get('total_trades', 0)} trades")
                with m_c9:
                    st.metric("Profit Factor", f"{m.get('profit_factor', 0.0):.2f}")
                with m_c10:
                    st.metric("TCA Friction Paid", f"${m.get('total_tca_cost_usd', 0.0):,.2f}")

                # Walk-Forward Efficiency (WFE) Card
                wfe_val = wfe.get("wfe_ratio", 0.0)
                is_robust = wfe.get("robustness_verdict") == "ROBUST_EDGE"
                badge_bg = "rgba(16,185,129,0.15)" if is_robust else "rgba(244,63,94,0.15)"
                badge_fg = "#10B981" if is_robust else "#F43F5E"
                st.markdown(f"""
                <div style="background:{badge_bg}; border:1px solid {badge_fg}; border-radius:8px; padding:12px 18px; margin:14px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#F8FAFC; font-size:0.95rem;">🔬 Walk-Forward Out-of-Sample Efficiency (WFE Ratio): <span style="color:{badge_fg}; font-family:monospace; font-size:1.05rem;">{wfe_val:.2f}</span></span>
                        <span style="background:{badge_fg}; color:#0F172A; font-weight:800; font-size:0.75rem; padding:3px 10px; border-radius:4px;">{wfe.get('robustness_verdict', 'N/A')}</span>
                    </div>
                    <div style="font-size:0.80rem; color:#94A3B8; margin-top:4px;">
                        In-Sample Avg Sharpe: <b style="color:#F8FAFC;">{wfe.get('in_sample_avg_sharpe', 0.0):.2f}</b> | 
                        Out-of-Sample Avg Sharpe: <b style="color:#F8FAFC;">{wfe.get('out_of_sample_avg_sharpe', 0.0):.2f}</b> | 
                        Standard Threshold: WFE &ge; 0.50 denotes non-overfitted institutional alpha.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Interactive Plotly Dual Curves
                dates = res.get("daily_dates", [])
                p_equity = res.get("daily_equity", [])
                b_equity = res.get("daily_benchmark", [])

                if dates and p_equity:
                    fig_curve = go.Figure()
                    fig_curve.add_trace(go.Scatter(
                        x=dates,
                        y=p_equity,
                        mode="lines",
                        name=f"Portfolio ({res.get('strategy')})",
                        line=dict(color="#10B981", width=2.5)
                    ))
                    if b_equity:
                        fig_curve.add_trace(go.Scatter(
                            x=dates,
                            y=b_equity,
                            mode="lines",
                            name=f"Benchmark ({res.get('benchmark', 'SPY')})",
                            line=dict(color="#38BDF8", width=1.5, dash="dash")
                        ))
                    fig_curve.update_layout(
                        title=f"Walk-Forward Cumulative Equity Curve vs {res.get('benchmark', 'SPY')} ($1,000,000.00 Base)",
                        xaxis_title="Date",
                        yaxis_title="Portfolio Valuation ($ USD)",
                        template="plotly_dark",
                        height=380,
                        margin=dict(l=20, r=20, t=40, b=20),
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_curve, use_container_width=True)

                    # Underwater Drawdown Curve
                    p_arr = np.array(p_equity, dtype=float)
                    peaks = np.maximum.accumulate(p_arr)
                    dd_pct = ((p_arr - peaks) / peaks) * 100.0

                    fig_dd = go.Figure()
                    fig_dd.add_trace(go.Scatter(
                        x=dates,
                        y=dd_pct,
                        mode="lines",
                        fill="tozeroy",
                        name="Drawdown %",
                        line=dict(color="#F43F5E", width=1.5),
                        fillcolor="rgba(244,63,94,0.25)"
                    ))
                    fig_dd.update_layout(
                        title="Peak-to-Trough Portfolio Underwater Drawdown (%)",
                        xaxis_title="Date",
                        yaxis_title="Drawdown (%)",
                        template="plotly_dark",
                        height=240,
                        margin=dict(l=20, r=20, t=35, b=20)
                    )
                    st.plotly_chart(fig_dd, use_container_width=True)

                # Walk-Forward Folds Breakdown Table
                windows = res.get("windows", [])
                if windows:
                    st.markdown("##### 🗓️ Walk-Forward Rolling Folds Breakdown")
                    st.dataframe(pd.DataFrame(windows), use_container_width=True)

                # Trade Logs
                trades = res.get("trades_log", [])
                if trades:
                    st.markdown("##### 📜 Out-of-Sample Trade Execution & TCA Log")
                    st.dataframe(pd.DataFrame(trades), use_container_width=True)

        with bt_sub2:
            st.markdown("#### 🤖 Autonomous Positive-Expectancy Strategy Scanner")
            st.caption("Scans watchlists for trades with E[PnL] > 0, Cornish-Fisher POP >= 65%, and automated Investment Committee approval.")

            sc_c1, sc_c2 = st.columns([3, 1])
            with sc_c1:
                scan_tickers_in = st.text_input(
                    "Scanner Universe (comma-separated)",
                    value="SPY, QQQ, AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, GLD",
                    help="Asset symbols to screen for positive econometric edge."
                )
            with sc_c2:
                min_pop_slider = st.slider("Min Cornish-Fisher POP (%)", min_value=50, max_value=85, value=65, step=5)

            scan_btn = st.button("🔍 Scan Universe for High-Expectancy Algo Trades", use_container_width=True, type="primary")

            if scan_btn:
                scan_list = [s.strip().upper() for s in scan_tickers_in.split(",") if s.strip()]
                with st.spinner("Analyzing higher-order moments, Cornish-Fisher quantiles, and transaction friction..."):
                    scanner = AlgoOpportunityScanner()
                    opps = scanner.scan_universe(tickers=scan_list, min_pop_cf=float(min_pop_slider) / 100.0)
                    st.session_state["scanned_algo_opps"] = opps

            opps = st.session_state.get("scanned_algo_opps")
            if opps is not None:
                st.divider()
                st.markdown(f"##### 🎯 Identified Opportunities ({len(opps)} Found)")
                if not opps:
                    st.info("No candidates passed the positive expectancy (E[PnL] > 0) and POP hurdle. Universe is currently under high tail-risk or compressed premium.")
                else:
                    for idx, opp in enumerate(opps):
                        v_color = "#10B981" if opp["committee_verdict"] == "APPROVED" else "#F59E0B"
                        with st.container():
                            st.markdown(f"""
                            <div style="background:rgba(18,24,36,0.85); border:1px solid #1E2638; border-left:4px solid {v_color}; border-radius:8px; padding:14px 18px; margin-bottom:12px;">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <div style="font-size:1.05rem; font-weight:800; color:#F8FAFC;">
                                        {opp['ticker']} <span style="font-size:0.80rem; font-weight:600; color:#38BDF8; margin-left:8px;">${opp['spot_price']:.2f}</span>
                                    </div>
                                    <div>
                                        <span style="background:rgba(255,255,255,0.06); color:#38BDF8; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:4px; margin-right:6px;">{opp['strategy_type']}</span>
                                        <span style="background:{v_color}; color:#0F172A; font-size:0.75rem; font-weight:800; padding:2px 8px; border-radius:4px;">{opp['committee_verdict']}</span>
                                    </div>
                                </div>
                                <div style="display:grid; grid-template-columns:repeat(5, 1fr); gap:10px; margin-top:10px; font-size:0.78rem;">
                                    <div><span style="color:#64748B;">Action:</span> <b style="color:#F8FAFC;">{opp['action']}</b></div>
                                    <div><span style="color:#64748B;">Cornish-Fisher POP:</span> <b style="color:#10B981;">{opp['pop_cf_pct']:.1f}%</b></div>
                                    <div><span style="color:#64748B;">Half-Kelly Alloc:</span> <b style="color:#38BDF8;">{opp['half_kelly_allocation_pct']:.1f}%</b></div>
                                    <div><span style="color:#64748B;">Expected PnL:</span> <b style="color:#10B981;">+${opp['expected_pnl_usd']:,.2f}</b></div>
                                    <div><span style="color:#64748B;">TCA Cost:</span> <b style="color:#F59E0B;">${opp['tca_cost_usd']:.2f}</b></div>
                                </div>
                                <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; margin-top:6px; font-size:0.74rem; color:#94A3B8;">
                                    <div>Vol: <b>{opp['annualized_vol_pct']:.1f}%</b></div>
                                    <div>Skewness: <b>{opp['skewness']:.2f}</b></div>
                                    <div>Kurtosis: <b>{opp['excess_kurtosis']:.2f}</b></div>
                                    <div>1D 99% CF-VaR: <b>{opp['cf_var_99_daily_pct']:.2f}%</b></div>
                                </div>
                                <div style="font-size:0.76rem; color:#94A3B8; margin-top:8px; border-top:1px solid #1E2638; padding-top:6px;">
                                    <b>Committee Rationale:</b> {opp['rationale']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            col_d1, col_d2 = st.columns([1.5, 4.5])
                            with col_d1:
                                if st.button(f"⚡ Dispatch {opp['ticker']} to SMART Router", key=f"disp_{opp['ticker']}_{idx}", use_container_width=True):
                                    with st.spinner(f"Routing {opp['ticker']} through Multi-Exchange Smart Router..."):
                                        try:
                                            # Route order via router
                                            router = st.session_state["multi_exchange_router"]
                                            route_res = router.route_order(
                                                ticker=opp["ticker"],
                                                asset_class="Options" if "OPTIONS" in opp["strategy_type"] else "Equities",
                                                side="BUY" if "BUY" in opp["action"] else "SELL",
                                                quantity=10.0 if "OPTIONS" in opp["strategy_type"] else 100.0,
                                                price=opp["spot_price"],
                                                preferred_venue="SMART"
                                            )
                                            # Dispatch Webhook Alert
                                            dispatcher = get_alert_dispatcher()
                                            dispatcher.dispatch_alert(
                                                alert_type="ALGO_STRATEGY_DISPATCH",
                                                title=f"⚡ Algo Trade Dispatched: {opp['ticker']} {opp['action']}",
                                                message=f"Autonomous scanner identified positive expectancy (+${opp['expected_pnl_usd']:,.2f}) with Cornish-Fisher POP {opp['pop_cf_pct']:.1f}%. Routed via {route_res.get('selected_venue', 'SMART')}.",
                                                severity="SUCCESS",
                                                metadata={
                                                    "ticker": opp["ticker"],
                                                    "strategy": opp["strategy_type"],
                                                    "pop_cf_pct": opp["pop_cf_pct"],
                                                    "expected_pnl": opp["expected_pnl_usd"],
                                                    "venue": route_res.get("selected_venue", "SMART"),
                                                    "receipt_hmac": route_res.get("execution_receipt", {}).get("receipt_hmac_sha256", "N/A")
                                                }
                                            )
                                            st.success(f"✅ Routed to {route_res.get('selected_venue', 'SMART')}! Status: {route_res.get('routing_status')} | Receipt: {route_res.get('execution_receipt', {}).get('receipt_hmac_sha256', 'N/A')[:16]}... Webhook alert broadcasted!")
                                        except Exception as e:
                                            st.error(f"Routing error: {str(e)}")
