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

Every financial figure and calculation is tracked in an immutable **Provenance Ledger** (`.provenance.json`) secured with true HMAC-SHA256 integrity signatures:

1. **Cryptographic HMAC Ledger Integrity**: Tool wrappers sign every ledger record with HMAC-SHA256 using `LEDGER_HMAC_KEY` from `.env`. **Plainly stated: this HMAC signature catches accidental or sloppy edits; the live re-fetch check is the real protection.**
2. **Independent Re-Fetch**: The verifier independently re-fetches primary SEC XBRL filings (filtering by form type `10-K` and exact period end date, e.g., `2025-09-27`) or yFinance quotes. Discrepancies between the live source and the ledger fail immediately as `SOURCE_REFETCH_DISCREPANCY`.
3. **Stated-Precision Half-Unit Rounding Tolerance**:
   - Tolerance dynamically depends on the number of decimal digits shown: $\Delta = 0.5 \times 10^{-d} \times \text{Scale}$.
   - `$416.2B` ($d=1, \text{scale}=10^9$) allows $\pm \$0.05\text{B}$ ($\pm \$50\text{M}$).
   - `46.91%` ($d=2, \text{scale}=1.0$) allows $\pm 0.005\%$ ($\pm 0.5\text{ bps}$).
   - Integer `12,715` ($d=0, \text{scale}=1.0$) allows $\pm 0.5$.
4. **Default-Deny Claim Detection**: Every sentence and table row must carry:
   - A valid ledger citation `[LEDGER_XXXX]`, OR
   - An `[ANALYSIS]` tag (deductive reasoning from verified data), OR
   - An `[UNVERIFIED: model memory]` tag (qualitative historical memory).
   - Any untagged figure, untracked cell, spelled-out word number (`six percent`, `93.7 billion dollars`), or malformed citation (`[ledger_0001]`) fails.
5. **Audit Reports**: Produces a companion audit file (`<REPORT>.audit.md`) with:
   - `### ✅ 1. Confirmed Claims`
   - `### ❌ 2. Wrong / Discrepant Figures`
   - `### ⚠️ 3. Unverifiable / Failed Claims`

---

## 🥊 Skeptic Agent (`/agents/skeptic.py`)

The **Skeptic Agent** acts as an adversarial red-team auditor designed to stress-test investment theses against DCF sensitivity models and empirical SEC filing evidence:

1. **Dynamic Thesis Extraction**: Automatically extracts stated growth rates, operating margins, and discount rates from thesis reports.
2. **Adversarial Stress Testing**:
   - Implied 5-year FCF CAGR via Reverse DCF.
   - `-200 bps` structural operating margin compression haircut.
   - `+100 bps` increase in discount rate / cost of capital (WACC).
3. **Empirical Filing Evidence**:
   - Working Capital Divergence: Receivables YoY vs Revenue YoY ($\Delta > 5.0\text{ pp}$ flags collection friction / DSO expansion) and Inventory YoY vs Revenue YoY.
   - Customer Concentration: Flags if single customer accounts for $> 10\%$ revenue.
   - Refinancing Risk: Short-term debt due in 12 months vs Cash & Equivalents ($> 50\%$ flags rollover risk).
4. **Quantitative Definition of "No Strong Counter-Evidence Found"**:
   A thesis qualifies for `"No strong counter-evidence found."` if and only if ALL criteria pass:
   - Implied 5Y FCF CAGR $\le \text{Historical 3Y FCF CAGR} + 2.0\text{ percentage points}$.
   - Valuation drop under $-200\text{ bps}$ margin shock is $\le 15\%$.
   - Valuation drop under $+100\text{ bps}$ WACC shock is $\le 15\%$.
   - Working capital divergence $\le 5.0\text{ pp}$.
   - Short-term debt due within 12 months $\le 50\%$ of liquid cash.
   - Max customer concentration $\le 10\%$.
   - Zero unaddressed empirical filing headwinds.

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
