# Meridian AI Connectors & Skill Integration

This directory contains external AI connectors that expose Meridian's quantitative research desks, options pricing, econometric probability simulator, and $1,000,000 paper trading execution engine to external AI models and assistants, including:

- **Anthropic Claude Desktop** & **Claude Code CLI** (via Model Context Protocol - MCP stdio)
- **Cursor** & **Windsurf** AI IDEs (via MCP Server configuration)
- **Groq Cloud** (Llama 3.3 70B, etc. via OpenAI-compatible function calling)
- **OpenAI** (GPT-4o, etc. via `FINANCIAL_TOOLS_SCHEMA`)
- **LangChain / LlamaIndex / Custom Agent Loops**

---

## Files Overview

1. **[`mcp_server.py`](mcp_server.py)**:
   A standard JSON-RPC 2.0 / MCP stdio server. Responds to protocol handshake, `tools/list`, and `tools/call`. Can be launched directly by Claude Desktop or Cursor.
2. **[`groq_connector.py`](groq_connector.py)**:
   Universal OpenAI and Groq tool definitions (`FINANCIAL_TOOLS_SCHEMA`), a direct tool execution dispatcher (`execute_tool_call`), and a multi-turn autonomous agent runner (`run_groq_agent`).
3. **[`claude_desktop_config.json`](claude_desktop_config.json)**:
   Ready-to-use configuration snippet for pasting into `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).
4. **[`SKILL.md`](SKILL.md)**:
   Complete Agent Skill specification documenting all 10 tools, input/output schemas, and multi-turn conversational examples.

---

## 10 Exposed Financial Tools

| Tool Name | Asset Class / Capability | Primary Output |
| :--- | :--- | :--- |
| `resolve_ticker` | Equities, Crypto, Commodities | Ticker, official company name, live price, ATM strike, IV % |
| `get_live_quote` | Multi-Asset Real-Time Feed | Last price, 24h change %, volume, currency, market status |
| `get_options_chain` | Equity & ETF Options | Expirations, ATM strike, PCR (OI), call/put contracts |
| `calculate_options_greeks` | Black-Scholes Analytics | Fair value, Delta, Gamma, Theta, Vega, Rho, Vanna, Volga |
| `analyze_options_strategy` | Multi-Leg Spreads | Net credit/debit, max profit, max loss, breakevens, payoff curve |
| `simulate_econometric_probability` | Econometrics & Risk Cones | PDF/CDF cones (+/- 1, 2, 3 $\sigma$), hitting time, Cornish-Fisher VaR |
| `execute_paper_trade` | \$1,000,000 Simulation Portfolio | Real-time order fill, cash balance deduction, HMAC-SHA256 receipt |
| `get_paper_portfolio` | Portfolio Book Management | Total equity, available cash, open positions, unrealized & realized P&L |
| `close_paper_position` | Trade Exit & P&L Realization | Position exit, cash credit, realized return %, signed receipt |
| `run_multi_asset_committee` | 5-Desk Quantitative Committee | Cross-asset allocations, stress test, margin checks, CRO signoff |

---

## Running Automated Verification
Run the connector test suite:
```bash
pytest tests/test_connectors.py -v
```
Run the full institutional test suite:
```bash
pytest
```
