# Crypto & 24/7 Derivatives Agent (`agents/crypto_derivatives_agent.py`)

## 1. System Role & Mission
The **Crypto & 24/7 Derivatives Agent** is an institutional specialist desk within the Meridian Multi-Asset Master Orchestrator, monitoring continuous around-the-clock digital asset derivative markets, perpetual swaps, and liquidation dynamics.

## 2. Core Capabilities
- **Perpetual Funding Rate Engine:** Annualizes 8-hour funding rates into compound APY carry, tracking market crowding and long/short skew.
- **Cash-and-Carry Basis Arbitrage:** Models net annual yields between spot and dated quarterly futures after round-trip maker/taker exchange fees and borrow costs.
- **Liquidation Cascade Modeling:**
  - Evaluates open interest to daily volume ratios.
  - Computes precise liquidation prices under isolated and cross-margin collateral regimes.
  - Flags flash wick liquidation vulnerability when adverse buffers fall below $8\%$.
- **24/7 Red Flags Engine:** Detects reckless leverage ($> 20\text{x}$), extreme funding dislocations ($> \pm 40\%$ APY), and exchange concentration hazards.
- **Cryptographic Provenance:** Records all perpetual funding analyses and liquidation assessments into `tools/ledger.py` with HMAC-SHA256 signatures.
