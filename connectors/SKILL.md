---
name: meridian-finance-workstation
description: Institutional Quantitative Trading, Options Risk, Econometric Probability Simulator, and $1,000,000 Paper Trading Engine for Claude, Groq, Cursor, Codex, and OpenAI.
---

# Meridian Financial Workstation & Quantitative Trading Skill

Connects external AI systems (Anthropic Claude, Groq Llama 3.3, Cursor, Windsurf, Codex, and OpenAI) directly to Meridian's institutional research workstation, specialized trading desks, econometric probability simulator, and \$1,000,000 live paper trading engine.

## 1. Supported AI Platforms & Protocols

| AI Platform | Connection Protocol | Configuration Path |
| :--- | :--- | :--- |
| **Anthropic Claude Desktop** | Model Context Protocol (MCP stdio) | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Claude Code (CLI)** | MCP Local Tool Server | `claude mcp add meridian-finance` |
| **Cursor & Windsurf IDEs** | MCP Server Settings | `.cursor/mcp.json` or Settings > MCP |
| **Groq (Llama 3.3 70B)** | OpenAI Function Calling (`tools=...`) | `connectors/groq_connector.py` |
| **OpenAI / LangChain** | OpenAI Function Calling (`tools=...`) | `FINANCIAL_TOOLS_SCHEMA` |

---

## 2. Quickstart Setup Guide

### Option A: Anthropic Claude Desktop
Open your Claude Desktop configuration file:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the `meridian-finance-workstation` entry under `mcpServers`:

```json
{
  "mcpServers": {
    "meridian-finance-workstation": {
      "command": "D:\\AI-Workspace\\finance agents for research\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "connectors.mcp_server"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```
*Restart Claude Desktop. The hammer/tools icon will appear with all 10 financial tools.*

---

### Option B: Claude Code CLI
Register the server directly with one command in your terminal:
```bash
claude mcp add meridian-finance -- "D:\AI-Workspace\finance agents for research\.venv\Scripts\python.exe" -m connectors.mcp_server
```

---

### Option C: Groq / OpenAI Python Integration
Use `connectors.groq_connector` to give any Groq or OpenAI model access to all financial tools:

```python
import os
from connectors.groq_connector import run_groq_agent, FINANCIAL_TOOLS_SCHEMA, execute_tool_call

# Set your Groq API key
os.environ["GROQ_API_KEY"] = "gsk_..."

# Run an agentic quantitative workflow
result = run_groq_agent(
    prompt="Resolve Micron, fetch its live market quote, and calculate Black-Scholes Greeks for the nearest ATM Call option.",
    model="llama-3.3-70b-versatile"
)

print(result["final_response"])
```

Or run via CLI:
```bash
python connectors/groq_connector.py --prompt "Check my paper portfolio cash balance and positions."
```

---

## 3. Available Tools & Schemas

The connector exposes 10 institutional-grade quantitative tools:

### 1. `resolve_ticker`
Resolves company names (e.g. `micron`, `apple`, `nvidia`, `tesla`) or direct symbols to official market tickers, live quote, nearest ATM strike, and ATM Implied Volatility.
- **Parameters**:
  - `query` (string, required): Company name or ticker.

### 2. `get_live_quote`
Fetches real-time price, day change, volume, currency, and market status for Equities, ETFs, Crypto, and Commodities.
- **Parameters**:
  - `symbol` (string, required): Symbol (e.g. `AAPL`, `BTC-USD`, `CL=F`).

### 3. `get_options_chain`
Fetches live multi-expiration options chains, strikes, bid/ask, open interest, PCR, and implied volatility.
- **Parameters**:
  - `symbol` (string, required): Underlying equity ticker.
  - `expiration` (string, optional): Expiration date (`YYYY-MM-DD`).

### 4. `calculate_options_greeks`
Computes Black-Scholes fair pricing and Greeks (Delta, Gamma, Theta, Vega, Rho, Vanna, Volga).
- **Parameters**:
  - `spot` (number, required): Underlying asset price.
  - `strike` (number, required): Option strike price.
  - `dte` (integer, required): Days to expiration.
  - `iv` (number, required): Implied volatility decimal (e.g. `0.35`).
  - `r` (number, optional): Risk-free rate (default: `0.045`).
  - `option_type` (string, optional): `'call'` or `'put'`.

### 5. `analyze_options_strategy`
Evaluates multi-leg options strategies (Iron Condor, Straddle, Vertical Spread, Collar, Covered Call). Returns net credit/debit, max profit, max loss, and breakevens.
- **Parameters**:
  - `symbol` (string, required): Underlying symbol.
  - `spot` (number, required): Current spot price.
  - `legs` (array of objects, required): List of legs with `strike`, `option_type`, `side`, `premium`, `quantity`, `dte`.

### 6. `simulate_econometric_probability`
Runs econometric simulations conforming to Black-Scholes and Bloomberg OVME standards: Log-normal PDF/CDF probability cones (+/- 1, 2, 3 sigma), target price hitting time, barrier touch probabilities, and Cornish-Fisher VaR/CVaR.
- **Parameters**:
  - `mode` (string, required): `'pdf_cdf'`, `'single_stock'`, `'options_strategy'`, `'cornish_fisher'`.
  - `spot` (number, required): Current spot price.
  - `dte` (integer, optional): Horizon in days.
  - `volatility` (number, optional): Annualized volatility decimal.
  - `target_price` (number, optional): Target price level.
  - `drift` (number, optional): Expected annualized drift.
  - `lower_barrier` (number, optional): Downside touch price.
  - `upper_barrier` (number, optional): Upside touch price.

### 7. `execute_paper_trade`
Executes an institutional paper order mirroring real live market prices against the **\$1,000,000.00** portfolio book.
- **Parameters**:
  - `symbol` (string, required): Asset ticker.
  - `asset_class` (string, required): `'Equities'`, `'Options'`, `'Futures'`, `'Crypto'`, `'Fixed Income'`.
  - `side` (string, required): `'BUY'` or `'SELL'`.
  - `quantity` (number, required): Quantity or contracts.
  - `price` (number, required): Execution price per unit.
  - `strategy_type` (string, optional): Strategy label.
  - `multiplier` (number, optional): Contract multiplier (e.g. `100` for options).
  - `margin_per_unit` (number, optional): Margin required per contract.
  - `notes` (string, optional): Rationale or trade thesis.

### 8. `get_paper_portfolio`
Retrieves live portfolio status: total equity, cash balance, open positions, unrealized P&L, realized P&L, and portfolio return %.
- **Parameters**: None.

### 9. `close_paper_position`
Closes an active position at current live market price (or specified exit price). Credits cash balance, realizes P&L, and generates an HMAC-SHA256 ledger receipt.
- **Parameters**:
  - `position_id` (string, required): Position identifier (e.g. `'POS_0001'`).
  - `exit_price` (number, optional): Exit price. If omitted, fetches live quote automatically.
  - `reason` (string, optional): Exit rationale (default: `'Market Close'`).

### 10. `run_multi_asset_committee`
Convenes the institutional 5-desk Investment Committee (Options Greek, Futures & Commodities, Fixed Income Macro, Crypto Derivatives, Cross-Asset Risk Officer) for complete stress testing, margin checks, and CRO signoff.
- **Parameters**:
  - `portfolio_name` (string, required): Portfolio label.
  - `total_capital` (number, required): Capital in USD (e.g. `1000000.0`).
  - `allocations` (object, required): Dollar allocation mapping across asset classes.

---

## 4. Multi-Turn Conversational Examples

### Example 1: Options Greek Analysis
**User Prompt to Claude / Groq:**
> *"What is Micron's current price, and what are the Black-Scholes Greeks for an ATM call expiring in 30 days?"*

**Tool Invocations:**
1. `resolve_ticker({"query": "micron"})` $\rightarrow$ Returns `MU`, spot `$105.40`, ATM strike `$105.00`, IV `36.2%`.
2. `calculate_options_greeks({"spot": 105.40, "strike": 105.00, "dte": 30, "iv": 0.362, "option_type": "call"})`
3. **Claude / Groq synthesizes**: Delta = +0.54, Gamma = 0.038, Theta = -\$0.082/day, Vega = \$0.118/1% IV.

---

### Example 2: Live Market Paper Trading
**User Prompt to Claude / Groq:**
> *"Buy 100 shares of Apple at the current market price in my paper trading account."*

**Tool Invocations:**
1. `get_live_quote({"symbol": "AAPL"})` $\rightarrow$ Spot = `$235.50`.
2. `execute_paper_trade({"symbol": "AAPL", "asset_class": "Equities", "side": "BUY", "quantity": 100, "price": 235.50, "notes": "Momentum long"})`
3. `get_paper_portfolio()` $\rightarrow$ Cash balance: `\$976,450.00`, Open positions: 1 (`POS_0001`), Total equity: `\$1,000,000.00`.
4. **Claude / Groq synthesizes**: Confirms execution with order ID, filled price, remaining cash, and cryptographic receipt.

---

## 5. Security & Provenance Guarantees
- **HMAC-SHA256 Cryptographic Receipts**: Every trade execution and closing is recorded in [`journal/ledger.jsonl`](file:///D:/AI-Workspace/finance%20agents%20for%20research/journal/ledger.jsonl) with an immutable cryptographic signature.
- **Zero Hallucinated Financials**: Market prices, options chains, and treasury yields are fetched directly from live financial data feeds.
- **Safe stdio Protocol**: Standard JSON-RPC 2.0 communication over isolated process streams with zero network exposure unless explicitly requested.
