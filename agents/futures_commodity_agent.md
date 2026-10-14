# Futures & Commodity Desk Agent (`agents/futures_commodity_agent.py`)

## 1. System Role & Mission
The **Futures & Commodity Desk Agent** manages physical commodity and financial futures positioning within the Meridian Multi-Asset Master Orchestrator. It monitors term structure curvature across Energy, Metals, Agriculture, and Index futures, computing roll yield carry and enforcing exchange margin discipline.

## 2. Core Capabilities
- **Cost-of-Carry Valuation:** Applies analytical models $F = S e^{(r + c - y)T}$ factoring financing rates, physical storage costs, and convenience yields.
- **Term Structure & Roll Yield:** Identifies Contango vs. Backwardation regimes across the curve and computes annualized roll decay/yield.
- **Exchange Margin & Leverage Stress-Testing:**
  - Evaluates Initial vs. Maintenance margin requirements across positions.
  - Computes max adverse percentage move before margin liquidation triggers.
  - Enforces institutional leverage limits ($\le 10\text{x}$) and margin utilization ceilings ($< 60\%$).
- **Red Flags Engine:** Flags hyper-leverage, severe contango drag ($> 10\%$ annual bleed), and tight margin call buffers.
- **Cryptographic Provenance:** Every curve calculation and margin stress audit is recorded in `tools/ledger.py` with an HMAC-SHA256 signature.
