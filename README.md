# Open-Source Stock and Market Research Toolkit

A modular stock, market, and financial research environment powered by **OpenBB Platform**, **yFinance**, **Federal Reserve (FRED)**, **SEC EDGAR**, **Calculation Toolkit**, **Verifier & Provenance Ledger**, and **Model Context Protocol (MCP)** servers.

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
├── agents\
│   ├── verifier.md            # Verifier agent specification & audit rules
│   ├── verifier.py            # Automated verification & re-fetch engine
│   ├── skeptic.md             # Skeptic agent specification & thesis destruction rules
│   └── skeptic.py             # Skeptic agent stress-testing engine
├── library\                   # Document store directory
│   ├── filings\               # Ingested regulatory filings (10-K, 10-Q, 20-F)
│   ├── transcripts\           # Earnings call transcripts
│   └── notes\                 # Analyst and research notes
├── alerts\                    # Automated event and filing alert monitor files
├── journal\                   # Investment decision journal and review files
├── backtests\                 # Quantitative screening and backtesting sandbox
├── reports\                   # Saved verified research reports & sidecar audits
├── scripts\                   # Utility and live-extraction scripts
│   └── test_queries.py
├── tools\
│   ├── ledger.py              # Immutable Provenance Ledger system with SHA-256 integrity
│   └── calc\                  # Tested deterministic financial calculation toolkit
│       ├── __init__.py
│       ├── metrics.py         # YoY, CAGR, Margins, ROIC, ROE, FCF, Net Debt/EBITDA, EV
│       ├── dcf.py             # Customizable DCF & Reverse DCF (implied growth)
│       └── fx.py              # Timestamped multi-currency conversion with quote dates
└── tests\
    ├── test_calc.py           # Unit test suite for calculation tools
    ├── test_verifier.py       # Unit test suite for Verifier agent & ledger
    ├── test_verifier_comprehensive.py # Re-fetch, SHA-256 tamper, rounding, and 8+ flawed sentences
    └── test_skeptic.py        # Unit test suite for Skeptic agent stress testing
```

---

## 🔍 Verifier Agent & Provenance Ledger (`/agents/verifier.py`)

Every financial figure and calculation is tracked in an immutable **Provenance Ledger** (`.provenance.json`) secured with SHA-256 HMAC integrity signatures:

1. **Cryptographic Ledger Integrity**: Tool wrappers compute SHA-256 hashes per entry. Hand-edited or injected ledger records fail immediately with `LEDGER_TAMPERED`.
2. **Independent Re-Fetch**: The verifier independently re-fetches cited SEC XBRL facts or yFinance market prices, catching discrepancies (`SOURCE_REFETCH_DISCREPANCY`) even if the report and local ledger agree.
3. **Strict Rounding Tolerance**:
   - Currency/Unit amounts: Relative error $|stated - raw| / raw \le 0.5\%$ (`0.005`).
   - Percentages/Ratios: Absolute margin error $|stated - raw| \le 0.10$ percentage points.
4. **Memory Tagging & Untracked Detection**: Qualitative claims from model memory must carry `[UNVERIFIED: model memory]`. Untagged narrative assertions trigger `UNTAGGED_MEMORY_CLAIM`, while numbers missing ledger IDs trigger `UNTRACKED_FIGURE`.
5. **Audit Reports**: Produces a companion audit file (`<REPORT>.audit.md`) with three structured sections:
   - `### ✅ 1. Confirmed Claims`
   - `### ❌ 2. Wrong / Discrepant Figures`
   - `### ⚠️ 3. Unverifiable / Failed Claims`

---

## 🥊 Skeptic Agent (`/agents/skeptic.py`)

The **Skeptic Agent** acts as an adversarial red-team auditor designed to destroy bull/bear investment theses before capital is committed:

1. **Hurdle Rate & Growth Feasibility**: Uses `reverse_dcf` to solve for the implied FCF growth rate embedded in current market prices, comparing it to historical 3-5Y CAGRs and industry averages.
2. **Stress Testing**: Applies quantitative shock models:
   - `-200 bps` structural operating margin contraction.
   - `+100 bps` increase in discount rate / cost of capital (WACC).
3. **Full Provenance**: Every figure cited by the skeptic carries its own valid ledger ID. Qualitative historical citations use `[UNVERIFIED: model memory]`.
4. **Output Format**:
   - `### 1. Counter-Evidence` (contradictory data points with ledger IDs)
   - `### 2. Under-appreciated Risks` (structural, regulatory, customer concentration)
   - `### 3. Alternative Explanations` (cyclical vs. secular, accounting vs. operational)
   - `### 4. What Would Change My Mind` (falsifiable quantitative triggers)
   - If the thesis withstands scrutiny and no counter-evidence exists: outputs `"No strong counter-evidence found."`

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
.\.venv\Scripts\pytest.exe tests/ -v
```
