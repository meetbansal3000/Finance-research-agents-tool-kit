# Options Greek Strategist Agent (`agents/options_greek_agent.py`)

## 1. System Role & Mission
The **Options Greek Strategist** is an institutional quantitative derivatives agent within the Meridian Multi-Asset Master Orchestrator ecosystem. It specializes in equity and index options, volatility surfaces, Black-Scholes-Merton sensitivity calculations, and multi-leg strategy risk architecture.

## 2. Core Capabilities
- **Exact Analytical Greeks:** Calculates 1st-order Greeks ($\Delta, \nu, \Theta, \rho$) and 2nd-order Greeks ($\Gamma, \text{Vanna}, \text{Volga}, \text{Charm}$) without numerical approximation shortcuts.
- **Volatility Surface & Skew:** Inverts market option prices via Brent's method to extract implied volatility across strikes and maturities.
- **Multi-Leg Payoff Engine:** Evaluates PnL distributions, net Greeks, breakeven thresholds, and max loss/profit for Straddles, Iron Condors, Vertical Spreads, Risk Reversals, and Collars.
- **Options Red Flags Engine:**
  - *Gamma Cliff Risk:* Warns when near-expiry options have accelerating gamma.
  - *Short Gamma Vulnerability:* Detects uncapped tail risk and negative gamma profiles subject to gap opens.
  - *Theta Burn Acceleration:* Detects daily time decay exceeding sustainable thresholds.
- **Cryptographic Provenance:** Every pricing run and Greek sensitivity vector is signed into `tools/ledger.py` with an HMAC-SHA256 signature.
