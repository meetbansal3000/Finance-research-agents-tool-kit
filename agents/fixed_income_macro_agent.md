# Fixed Income Macro Agent (`agents/fixed_income_macro_agent.py`)

## 1. System Role & Mission
The **Fixed Income Macro Agent** governs sovereign bond yield curve analysis, interest rate duration risk, and macroeconomic monetary policy shifts within the Meridian Multi-Asset Master Orchestrator.

## 2. Core Capabilities
- **Bond Valuation & Sensitivities:** Calculates Macaulay duration, Modified duration, analytical Convexity, and DV01 ($ value of 1 bp shift per bond and per million par).
- **Yield Shock Stress Matrix:** Simulates price movements across interest rate shock grids (-200 bps to +200 bps) utilizing 2nd-order Taylor expansions.
- **Yield Curve Macro Regime:**
  - Evaluates benchmark US Treasury curve points (3M, 2Y, 5Y, 10Y, 30Y).
  - Tracks 2Y-10Y and 3M-10Y yield spreads, detecting yield curve inversions and recession signals.
  - Classifies macro regimes: Normal, Inverted, Bull/Bear Steepeners, and Flatteners.
- **Red Flags Engine:** Flags deep curve inversions, ultra-long duration vulnerability ($> 12$ years), and negative convexity hazards.
- **Cryptographic Provenance:** Records all duration and curve metrics into `tools/ledger.py` with HMAC-SHA256 signatures.
