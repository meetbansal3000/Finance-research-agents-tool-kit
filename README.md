# Open-Source Stock and Market Research Toolkit

A modular stock, market, and financial research environment powered by **OpenBB Platform**, **yFinance**, **Federal Reserve (FRED)**, **SEC EDGAR**, **Calculation Toolkit**, and **Model Context Protocol (MCP)** servers.

---

## 📁 Project Structure

```
D:\AI-Workspace\finance agents for research\
├── .agents\
│   ├── rules\
│   │   └── research_rules.md  # Antigravity standing rules & calculation enforcement
│   └── mcp_config.json        # Project-level MCP configuration for Antigravity
├── .env                       # Environment variables (SEC User Agent, UTF-8)
├── .gitignore                 # Git ignore file
├── mcp_config.json            # Root MCP server registration file
├── pytest.ini                 # Pytest configuration
├── requirements.txt           # Python dependency lockfile
├── research_playbook_v2.md    # Master research workflows and standing rules
├── test_queries.py            # Verification script for SEC & OpenBB queries
├── watchlist.txt              # Active research coverage watchlist
├── tools\
│   └── calc\                  # Tested deterministic financial calculation toolkit
│       ├── __init__.py
│       ├── metrics.py         # YoY, CAGR, Margins, ROIC, ROE, FCF, Net Debt/EBITDA, EV
│       ├── dcf.py             # Customizable DCF & Reverse DCF (implied growth)
│       └── fx.py              # Timestamped multi-currency conversion
├── tests\
│   └── test_calc.py           # Unit test suite for calculation tools
├── reports\                   # Saved institutional research memos & deep dives
└── README.md                  # Setup, restart, and operational documentation
```

---

## 🧮 Calculation Toolkit (`/tools/calc/`)

To ensure mathematical precision across all research tasks, **agents never calculate numbers manually**. All metrics are computed using deterministic, tested functions that return exact outputs, formulas, and inputs:

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
Open PowerShell in this directory:
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If recreating from scratch)*:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
openbb-build
```

---

### 2. Environment Configuration (`.env`)
```env
SEC_EDGAR_USER_AGENT="Research Analyst research.analyst@example.com"
EDGAR_IDENTITY="Research Analyst research.analyst@example.com"
PYTHONUTF8="1"
```

---

### 3. Starting the MCP Servers

#### Option A: OpenBB MCP Server (1,188 Tools)
```powershell
$env:PYTHONUTF8="1"
.\.venv\Scripts\openbb-mcp.exe --transport stdio
```

#### Option B: SEC EDGAR MCP Server
```powershell
$env:SEC_EDGAR_USER_AGENT="Research Analyst research.analyst@example.com"
$env:PYTHONUTF8="1"
.\.venv\Scripts\sec-edgar-mcp.exe --transport stdio
```

---

## 🧪 Testing with Real Queries

Run the automated verification suite:
```powershell
$env:PYTHONUTF8="1"
.\.venv\Scripts\python.exe test_queries.py
```
