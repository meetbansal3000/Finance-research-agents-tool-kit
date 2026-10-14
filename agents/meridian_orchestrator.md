# Meridian Multi-Asset Master Orchestrator (`agents/meridian_orchestrator.py`)

## 1. System Topology & Architecture
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MERIDIAN MULTI-ASSET MASTER ORCHESTRATOR                 │
└──────┬───────────────┬──────────────┬──────────────┬──────────────┬─────────┘
       │               │              │              │              │
       ▼               ▼              ▼              ▼              ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│Options Greek ││Futures &     ││Fixed Income  ││Crypto & 24/7 ││Cross-Asset   │
│Strategist    ││Commodity     ││Macro Agent   ││Derivatives   ││Risk Officer  │
│              ││Desk Agent    ││              ││Agent         ││              │
└──────────────┘└──────────────┘└──────────────┘└──────────────┘└──────────────┘
```

The **Meridian Multi-Asset Master Orchestrator** is the top-level institutional coordinating intelligence within the `Finance Research Agents Tool-Kit`. It manages cross-asset allocations, coordinates execution across five specialized quantitative trading and risk desks, enforces strict risk gatekeeping, and produces audited investment committee memorandums.

## 2. Specialized Desk Roster
1. **Options Greek Strategist (`agents/options_greek_agent.py`):**
   - First-order ($\Delta, \nu, \Theta, \rho$) and second-order ($\Gamma, \text{Vanna}, \text{Volga}, \text{Charm}$) Greeks.
   - Volatility surface calibration, skew dynamics, multi-leg strategy payoffs, and delta-hedging overlays.
2. **Futures & Commodity Desk Agent (`agents/futures_commodity_agent.py`):**
   - Cost-of-carry theoretical pricing: Energy, Metals, Agriculture, and Index futures.
   - Term structure curve curvature (Contango vs Backwardation) and annualized roll yield decay/boost.
   - Exchange Initial & Maintenance margin auditing, leverage buffers, and liquidation thresholds.
3. **Fixed Income Macro Agent (`agents/fixed_income_macro_agent.py`):**
   - Sovereign yield curve structure (3M, 2Y, 5Y, 10Y, 30Y) and 2Y-10Y curve inversion warning signals.
   - Macaulay duration, Modified duration, Convexity, and DV01 ($ per bp).
   - Rate shock scenario modeling across -200 bps to +200 bps.
4. **Crypto & 24/7 Derivatives Agent (`agents/crypto_derivatives_agent.py`):**
   - Perpetual swap funding rates, 8h carry, and compound APY annualization.
   - Cash-and-carry basis arbitrage yields between spot and dated quarterly futures.
   - Liquidation cascade risk modeling, open-interest-to-volume ratios, and liquidation buffer metrics.
5. **Cross-Asset Risk Officer (`agents/cross_asset_risk_officer.py`):**
   - Unified Parametric Value-at-Risk (VaR at 95% and 99%) and Expected Shortfall ($CVaR$).
   - Historical black swan crisis stress testing (2008 GFC, 2020 Covid, 2022 Fed rate shocks).
   - Authoritative gatekeeper issuing binding verdicts (`APPROVED`, `CONDITIONAL_APPROVAL`, `REJECTED`) and centralizing the master Red Flags Registry.

## 3. Cryptographic Provenance Ledger
Every data extraction, pricing model output, risk evaluation, and committee decision is anchored in [`tools/ledger.py`](../tools/ledger.py) generating tamper-proof `[LEDGER_XXXX]` HMAC-SHA256 signatures.
