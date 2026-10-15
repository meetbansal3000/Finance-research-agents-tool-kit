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

    # 6 Specialized Sub-Tabs
    tab_orch, tab_opt, tab_fut, tab_fi, tab_crypto, tab_risk = st.tabs([
        "🏛️ Master Orchestrator",
        "🎯 Options Greek Strategist",
        "🌾 Futures & Commodity Desk",
        "📈 Fixed Income Macro Agent",
        "⚡ Crypto & 24/7 Derivatives",
        "🛡️ Cross-Asset Risk Officer & Red Flags"
    ])

    # =========================================================================
    # TAB 1: MASTER ORCHESTRATOR (Multi-Desk Committee Review)
    # =========================================================================
    with tab_orch:
        st.markdown("### 🏛️ Institutional Multi-Asset Committee Review")
        st.caption("Coordinate execution across all 5 specialized desks, aggregate portfolio risk, and enforce independent CRO gatekeeping.")

        col_cfg1, col_cfg2 = st.columns([1.2, 2.0])
        with col_cfg1:
            st.markdown("#### 💼 Portfolio Specification")
            port_name = st.text_input("Portfolio / Mandate Name", value="Meridian Global Macro Alpha Fund", key="mo_port_name")
            total_cap = st.number_input("Total Capital Allocation ($USD)", min_value=100_000.0, max_value=1_000_000_000.0, value=10_000_000.0, step=500_000.0, key="mo_total_cap")

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
            c1.metric("Equities", f"${allocations['equities']:,.0f}", f"{eq_pct:.1f}%")
            c2.metric("Fixed Income", f"${allocations['fixed_income']:,.0f}", f"{fi_pct:.1f}%")
            c3.metric("Commodities", f"${allocations['commodities']:,.0f}", f"{comm_pct:.1f}%")
            c4.metric("Crypto 24/7", f"${allocations['crypto']:,.0f}", f"{cryp_pct:.1f}%")
            c5.metric("Options Overlay", f"${allocations['options_overlay']:,.0f}", f"{opt_pct:.1f}%")

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

        col_opt_mode1, col_opt_mode2 = st.columns([1, 2])
        with col_opt_mode1:
            st.markdown("#### ⚙️ Single Contract Evaluator")
            opt_ticker = st.text_input("Underlying Ticker", value="NVDA", key="opt_tk")
            opt_spot = st.number_input("Spot Price ($)", min_value=1.0, value=125.0, step=1.0, key="opt_sp")
            opt_strike = st.number_input("Strike Price ($)", min_value=1.0, value=130.0, step=1.0, key="opt_sk")
            opt_dte = st.number_input("Days to Expiration (DTE)", min_value=1, value=45, step=1, key="opt_dt")
            opt_vol_pct = st.number_input("Implied Volatility (%)", min_value=1.0, max_value=300.0, value=35.0, step=1.0, key="opt_vl")
            opt_r_pct = st.number_input("Risk-Free Rate (%)", min_value=0.0, max_value=20.0, value=4.5, step=0.1, key="opt_rf")
            opt_type = st.radio("Option Type", ["Call", "Put"], horizontal=True, key="opt_tp")

            expiry_years = opt_dte / 365.0
            vol_decimal = opt_vol_pct / 100.0
            r_decimal = opt_r_pct / 100.0

            opt_res = orchestrator.options_desk.analyze_contract(
                underlying_ticker=opt_ticker,
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
            c_g1.metric("Fair Value", f"${g['price']:.2f}", f"Intrinsic: ${g['intrinsic_value']:.2f}")
            c_g2.metric("Delta (Δ)", f"{g['delta']:+.4f}", f"{opt_res['hedging_delta_shares_per_contract']} shares")
            c_g3.metric("Gamma (Γ)", f"{g['gamma']:.6f}", "dΔ / dSpot")
            c_g4.metric("Vega (ν)", f"${g['vega']:.2f}", "per 1% Vol")

            c_g5, c_g6, c_g7, c_g8 = st.columns(4)
            c_g5.metric("Daily Theta (Θ)", f"${g['theta_daily']:.3f}/day", f"${g['theta_annual']:.2f}/yr")
            c_g6.metric("Rho (ρ)", f"${g['rho']:.3f}", "per 1% Rate")
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
                underlying_ticker=opt_ticker,
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
            fig_pnl.add_vline(x=opt_spot, line_dash="dot", line_color="#38BDF8", annotation_text="Current Spot")
            fig_pnl.update_layout(
                title=f"{strat_choice} Payoff at Expiration ({opt_ticker})",
                xaxis_title="Underlying Spot Price ($)",
                yaxis_title="Net PnL ($)",
                template="plotly_dark",
                height=320,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_pnl, use_container_width=True)

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Structure", sa["structure"], f"${sa['net_debit_credit']:.2f}")
            sc2.metric("Net Delta", f"{sa['net_delta']:+.3f}", "Directional bias")
            sc3.metric("Net Vega", f"${sa['net_vega']:.2f}", "per 1% Vol")
            sc4.metric("Net Daily Theta", f"${sa['net_theta_daily']:.2f}/day", "Time carry")

    # =========================================================================
    # TAB 3: FUTURES & COMMODITY DESK
    # =========================================================================
    with tab_fut:
        st.markdown("### 🌾 Futures & Commodity Desk")
        st.caption("Term structure curve analysis, Contango vs. Backwardation roll yields, and exchange leverage & margin buffer auditing.")

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
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Effective Leverage", f"{ma['effective_leverage']:.1f}x", "Institutional Limit: 10x")
        m2.metric("Margin Utilization", f"{ma['margin_utilization_pct']:.1f}%", ma["risk_status"])
        m3.metric("Free Headroom", f"${ma['free_margin_headroom']:,.0f}", "Buffer")
        m4.metric("Margin Call Price", f"${ma['margin_call_trigger_price']:.2f}", f"-{ma['max_adverse_move_pct']:.1f}% adverse")
        m5.metric("Audit Verdict", margin_res["verdict"], "Risk Cap Checked")

    # =========================================================================
    # TAB 4: FIXED INCOME MACRO AGENT
    # =========================================================================
    with tab_fi:
        st.markdown("### 📈 Fixed Income Macro Agent")
        st.caption("Sovereign yield curve inversion tracking, Macaulay & Modified duration, Convexity, DV01 ($ per bp), and interest rate shocks.")

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
        bm1.metric("Clean / Dirty Price", f"${bm['price']:.2f}", f"Par ${b_face:,.0f}")
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

        col_cr1, col_cr2 = st.columns([1.1, 1.9])
        with col_cr1:
            st.markdown("#### 🪙 Perpetual Swap Microstructure")
            cr_sym = st.selectbox("Asset Contract", ["BTC-PERP", "ETH-PERP", "SOL-PERP"], key="cr_sym")
            cr_spot = st.number_input("Spot Index ($)", min_value=1.0, value=65000.0, step=500.0, key="cr_sp")
            cr_mark = st.number_input("Perp Mark Price ($)", min_value=1.0, value=65080.0, step=500.0, key="cr_mk")
            cr_f8 = st.number_input("Current 8h Funding Rate (%)", value=0.012, step=0.005, format="%.4f", key="cr_f8")
            cr_oi = st.number_input("Open Interest ($USD)", value=1_500_000_000.0, step=100_000_000.0, key="cr_oi")
            cr_vol = st.number_input("24h Volume ($USD)", value=5_000_000_000.0, step=500_000_000.0, key="cr_vl")

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
            b1.metric("Gross Basis APY", f"{ba['gross_annualized_apy_pct']:+.2f}%", f"+${ba['gross_basis']:.2f}")
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

    # =========================================================================
    # TAB 6: CROSS-ASSET RISK OFFICER & RED FLAGS
    # =========================================================================
    with tab_risk:
        st.markdown("### 🛡️ Cross-Asset Risk Officer & Red Flags Registry")
        st.caption("Parametric & Historical Value-at-Risk (VaR), Expected Shortfall (CVaR), Correlation Heatmaps, Crisis Stress Matrix, and Institutional Red Flags.")

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
