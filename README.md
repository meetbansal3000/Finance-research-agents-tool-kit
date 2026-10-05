# Open-Source Stock and Market Research Toolkit

A modular stock, market, and financial research environment powered by **OpenBB Platform**, **yFinance**, **Federal Reserve (FRED)**, **SEC EDGAR**, **Calculation Toolkit**, and **Model Context Protocol (MCP)** servers.

---

## 📁 Clean Project Structure

```
D:\AI-Workspace\finance agents for research\
├── .agents\
│   ├── rules\
│   │   └── research_rules.md  # Antigravity standing rules & calculation enforcement
│   └── mcp_config.json        # Workspace-level MCP configuration for Antigravity
├── .env                       # Environment variables (SEC User Agent, UTF-8) - NOT committed
├── .env.example               # Template environment configuration
├── .gitignore                 # Git ignore file
├── pytest.ini                 # Pytest configuration
├── requirements.txt           # Pinned Python dependency lockfile
├── research_playbook_v2.md    # Master research workflows and standing rules
├── watchlist.txt              # Active research coverage watchlist
├── agents\                    # Agent specification and prompts directory (/agents)
├── library\                   # Document store directory
│   ├── filings\               # Ingested regulatory filings (10-K, 10-Q, 20-F)
│   ├── transcripts\           # Earnings call transcripts
│   └── notes\                 # Analyst and research notes
├── alerts\                    # Automated event and filing alert monitor files
├── journal\                   # Investment decision journal and review files
├── backtests\                 # Quantitative screening and backtesting sandbox
├── reports\                   # Saved verified institutional research memos
├── scripts\                   # Utility and testing scripts
│   ├── generate_report.py
│   ├── generate_multi_stock_reports.py
│   └── test_queries.py
├── tools\
│   └── calc\                  # Tested deterministic financial calculation toolkit
│       ├── __init__.py
│       ├── metrics.py         # YoY, CAGR, Margins, ROIC, ROE, FCF, Net Debt/EBITDA, EV
│       ├── dcf.py             # Customizable DCF & Reverse DCF (implied growth)
│       └── fx.py              # Timestamped multi-currency conversion with source tracking
└── tests\
    └── test_calc.py           # Unit test suite for calculation tools
```

---

## 🧮 Calculation Toolkit (`/tools/calc/`)

Agents never perform mental or rough arithmetic. All metrics are computed using deterministic functions:

| Function | Module | Description | Formula / Output |
| :--- | :--- | :--- | :--- |
| `yoy_growth` | `tools.calc.metrics` | Year-over-Year Growth | `((curr - prior) / abs(prior)) * 100` |
| `cagr` | `tools.calc.metrics` | Compound Annual Growth Rate | `((end / start) ** (1/n) - 1) * 100` |
| `margin` | `tools.calc.metrics` | Gross, Operating, Net Margins | `(numerator / revenue) * 100` |
| `roic` | `tools.calc.metrics` | Return on Invested Capital | `(NOPAT / Invested Capital) * 100` |
| `roe` | `tools.calc.metrics` | Return on Equity | `(Net Income / Equity) * 100` |
| `free_cash_flow` | `tools.calc.metrics` | Free Cash Flow | `CFO - CapEx` |
| `fcf_yield` | `tools.calc.metrics` | FCF Yield | `(FCF / Market Cap) * 100` |
| `net_debt_to_ebitda`| `tools.calc.metrics` | Leverage Ratio | `(Total Debt - Cash) / EBITDA` |
| `interest_coverage`| `tools.calc.metrics` | Interest Coverage | `EBIT / abs(Interest Expense)` |
| `cash_conversion` | `tools.calc.metrics` | Cash Conversion | `(CFO / Net Income) * 100` |
| `enterprise_value` | `tools.calc.metrics` | Enterprise Value | `Market Cap + Debt - Cash` |
| `ev_multiples` | `tools.calc.metrics` | EV/EBITDA, EV/Sales, EV/EBIT| `EV / Financial Metric` |
| `dcf` | `tools.calc.dcf` | Discounted Cash Flow Valuation| Full explicit + terminal value model |
| `reverse_dcf` | `tools.calc.dcf` | Implied Growth Rate Solver | Bisection solver for implied FCF CAGR|
| `convert_currency` | `tools.calc.fx` | FX Rate Conversion with Date | Spot / Historical rates via Yahoo Finance |

### Running Unit Tests:
```powershell
.\.venv\Scripts\pytest.exe tests/test_calc.py -v
```

---

## 🚀 Quick Setup & Restart Instructions

### 1. Activate the Python Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Environment Configuration (`.env`)
```env
SEC_EDGAR_USER_AGENT="Research Analyst research.analyst@example.com"
EDGAR_IDENTITY="Research Analyst research.analyst@example.com"
PYTHONUTF8="1"
```

### 3. Starting the MCP Servers

#### OpenBB MCP Server (1,188 Tools)
```powershell
$env:PYTHONUTF8="1"
.\.venv\Scripts\openbb-mcp.exe --transport stdio
```

#### SEC EDGAR MCP Server
```powershell
$env:SEC_EDGAR_USER_AGENT="Research Analyst research.analyst@example.com"
$env:PYTHONUTF8="1"
.\.venv\Scripts\sec-edgar-mcp.exe --transport stdio
```
