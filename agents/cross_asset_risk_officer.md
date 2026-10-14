# Cross-Asset Risk Officer Agent (`agents/cross_asset_risk_officer.py`)

## 1. System Role & Mission
The **Cross-Asset Risk Officer** acts as the Chief Risk Officer (CRO) and independent gatekeeper within the Meridian Multi-Asset Master Orchestrator. It monitors total portfolio risk, enforces capital limits, computes Parametric VaR and Expected Shortfall (CVaR), runs crisis stress tests, and maintains the authoritative institutional Red Flags Registry.

## 2. Core Capabilities
- **Parametric VaR & CVaR Engine:**
  - Evaluates portfolio volatility across Equities, Fixed Income, Commodities, Crypto, and Options overlays.
  - Computes 1-day and 10-day 95% and 99% Value-at-Risk and Expected Shortfall ($CVaR$).
- **Historical Crisis Stress Testing:**
  - Simulates portfolio shocks under black swan historical events: 2008 Global Financial Crisis, 2020 Covid Meltdown, 2022 Stagflation / Fed Rate Spike, and Algorithmic Flash Crash Deleveraging.
  - Flags any scenario with $> 25\%$ capital impairment as a CRITICAL violation.
- **Master Red Flags Registry & Gatekeeping:**
  - Consolidates red flags from all 5 desks into a centralized, severity-categorized audit log.
  - Issues binding investment committee verdicts: `APPROVED`, `CONDITIONAL_APPROVAL`, or `REJECTED`.
- **Cryptographic Provenance:** Records all risk evaluations into `tools/ledger.py` with HMAC-SHA256 signatures.
