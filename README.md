# Open-Source Stock and Market Research Toolkit

A modular stock, market, and financial research environment powered by **OpenBB Platform**, **yFinance**, **Federal Reserve (FRED)**, **SEC EDGAR**, and **Model Context Protocol (MCP)** servers.

---

## 📁 Project Structure

```
D:\AI-Workspace\finance agents for research\
├── .agents\
│   └── mcp_config.json        # Project-level MCP configuration for Antigravity
├── .env                       # Environment variables (SEC User Agent, UTF-8)
├── .gitignore                 # Git ignore file
├── mcp_config.json            # Root MCP server registration file
├── requirements.txt           # Python dependency lockfile
├── test_queries.py            # Verification script for SEC & OpenBB queries
└── README.md                  # Setup, restart, and operational documentation
```

---

## 🚀 Quick Setup & Restart Instructions

### 1. Activate the Python Virtual Environment
Open PowerShell in this directory:
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If you need to recreate the venv from scratch)*:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
openbb-build
```

---

### 2. Environment Configuration (`.env`)
Ensure your `.env` file exists with your SEC EDGAR User-Agent identity and UTF-8 encoding flag:
```env
SEC_EDGAR_USER_AGENT="Research Analyst research.analyst@example.com"
EDGAR_IDENTITY="Research Analyst research.analyst@example.com"
PYTHONUTF8="1"
```
> [!NOTE]
> The SEC requires User-Agent headers to follow the format: `Sample Company Name AdminContact@<sample company domain>.com`.

---

### 3. Starting the MCP Servers

#### Option A: OpenBB MCP Server
To run OpenBB MCP server directly over standard input/output:
```powershell
$env:PYTHONUTF8="1"
.\.venv\Scripts\openbb-mcp.exe --transport stdio
```

Or over HTTP / SSE on port 8001:
```powershell
$env:PYTHONUTF8="1"
.\.venv\Scripts\openbb-mcp.exe --transport streamable-http --host 127.0.0.1 --port 8001
```

#### Option B: SEC EDGAR MCP Server
To run SEC EDGAR MCP server:
```powershell
$env:SEC_EDGAR_USER_AGENT="Research Analyst research.analyst@example.com"
$env:PYTHONUTF8="1"
.\.venv\Scripts\sec-edgar-mcp.exe --transport stdio
```

---

## ⚙️ Antigravity MCP Server Registration

Both MCP servers are registered in `mcp_config.json` and `.agents/mcp_config.json`:

```json
{
  "mcpServers": {
    "openbb": {
      "command": "D:\\AI-Workspace\\finance agents for research\\.venv\\Scripts\\openbb-mcp.exe",
      "args": [
        "--transport",
        "stdio"
      ],
      "env": {
        "PYTHONUTF8": "1"
      }
    },
    "sec-edgar": {
      "command": "D:\\AI-Workspace\\finance agents for research\\.venv\\Scripts\\sec-edgar-mcp.exe",
      "args": [
        "--transport",
        "stdio"
      ],
      "env": {
        "SEC_EDGAR_USER_AGENT": "Research Analyst research.analyst@example.com",
        "EDGAR_IDENTITY": "Research Analyst research.analyst@example.com",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

To enable these servers across all Antigravity workspaces globally, copy the entries above into:
`~/.gemini/config/mcp_config.json`

---

## 🧪 Testing with Real Queries

Run the automated verification suite:
```powershell
$env:PYTHONUTF8="1"
.\.venv\Scripts\python.exe test_queries.py
```

### Verified Sample Outputs:
1. **Apple Inc. (AAPL) Quarterly Revenue from SEC Filings**:
   - **FY2026 Q3 (2026-03-29 to 2026-06-27)**: \$109.42B USD
   - **FY2026 Q2 (2025-12-28 to 2026-03-28)**: \$111.18B USD
   - **FY2026 Q1 (2025-09-28 to 2025-12-27)**: \$143.76B USD
   - **FY2025 Q3 (2025-03-30 to 2025-06-28)**: \$94.04B USD
   - *SEC Filing CIK*: `0000320193` ([SEC EDGAR Directory](https://www.sec.gov/edgar/browse/?CIK=0000320193))

2. **Microsoft Corp. (MSFT) Market Data**:
   - **Latest Close**: \$525.18 USD
   - **52-Week Range**: \$349.20 – \$553.72 USD
   - **Provider**: OpenBB yfinance endpoint (`obb.yfinance.equity.price.historical`)

---

## 🏢 Phase 2: Multi-Agent Parallel Research Architecture

When scaling research workloads, dispatch specialized subagents in parallel:

```
                  ┌──────────────────────┐
                  │ Synthesizer Agent    │
                  │ (Unified Report)     │
                  └──────────┬───────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Filings      │      │ Market Data  │      │ News /       │
│ Analyst      │      │ Analyst      │      │ Sentiment    │
│ (10-K, 10-Q) │      │ (OpenBB/FRED)│      │ Scout        │
└──────────────┘      └──────────────┘      └──────────────┘
```

- **Filings Analyst**: Reads 10-Ks, 10-Qs, 8-Ks; extracts risk factors, gross/operating margins, management guidance, and segment breakdown.
- **Market Data Analyst**: Retrieves prices, valuation ratios (P/E, EV/EBITDA), macroeconomic indicators (Fed rates, inflation), and peer comparisons.
- **News & Sentiment Scout**: Web scraping, press release analysis, earnings call highlights, and sentiment tracking.
- **Synthesizer**: Combines outputs into an institutional-grade investment memorandum citing exact filing URLs and endpoints for all figures.
