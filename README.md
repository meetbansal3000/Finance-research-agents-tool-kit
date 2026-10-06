# Open-Source Stock and Market Research Toolkit

A modular stock, market, and financial research environment powered by **OpenBB Platform**, **yFinance**, **Federal Reserve (FRED)**, **SEC EDGAR**, **Calculation Toolkit**, **Verifier & Provenance Ledger**, and **Model Context Protocol (MCP)** servers.

---

## ⚠️ Scope, Limitations, and Grounding

To be explicit about the true capabilities and operational boundaries of this toolkit:
1. **US SEC Filers Only for Direct XBRL**: Automated XBRL fact extraction and CIK resolution currently support US SEC filers only. Non-US filers (such as Indian BSE/NSE companies like TCS, European or UK filers) cannot use SEC EDGAR XBRL endpoints and require the dedicated audited corporate filing extractor (`tools/filing.py`) or direct document ingestion.
2. **Free Source Rate Limits**: Free external data sources operate under strict rate limits (SEC EDGAR max 10 req/sec; yfinance ~2,000 req/hr; Finnhub 60 req/min; FMP 5 req/min and 250 req/day; Alpha Vantage 5 req/min and 25 req/day). Local disk caching with TTL is active to conserve quotas, but requests are bounded by provider allowances.
3. **Verifier Flaw Detection Scope**: The Verifier catches the specific listed flaw types:
   - Missing ledger citations on quantitative figures under default-deny.
   - Cryptographic HMAC ledger tampering.
   - Values outside stated-precision half-unit tolerance boundaries.
   - Metric type contradictions (e.g., claiming a percentage on a base currency level).
   - Period and quarter mismatches (including planted prior-year figures).
   - Currency / unit labeling mismatches.
   - Adversarial prompt injection attempts aimed at manipulating verification rules.
   The Verifier does *not* catch all possible real-world errors outside these structural checks.
4. **No Silent Replacements**: Fallback data sources never silently replace SEC data; each figure carries an explicit provider source tag in the Provenance Ledger.

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
│   ├── analyst.md             # Analyst agent specification & playbook workflow rules
│   ├── analyst.py             # Analyst agent execution & error correction engine
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
│   └── TICKER_YYYY-MM-DD\     # Automated pipeline dossier outputs
├── run_research.py            # Upgrade 4: End-to-end autonomous research orchestrator
├── scripts\                   # Utility and live-extraction scripts
│   └── test_queries.py
├── tools\
│   ├── ledger.py              # Immutable Provenance Ledger system with SHA-256 integrity
│   ├── filing.py              # Audited filing extractor (SEC 10-K, NSE/BSE)
│   ├── knowledge.py           # Upgrade 5: Chroma-powered local knowledge base engine
│   ├── data_layer.py          # Upgrade 6: Multi-source fallback data layer & disk cache
│   └── calc\                  # Tested deterministic financial calculation toolkit
│       ├── __init__.py
│       ├── metrics.py         # YoY, CAGR, Margins, ROIC, ROE, FCF, Net Debt/EBITDA, EV
│       ├── dcf.py             # Customizable DCF & Reverse DCF (implied growth)
│       └── fx.py              # Timestamped multi-currency conversion with quote dates
└── tests\
    ├── test_calc.py           # Unit test suite for calculation tools
    ├── test_verifier.py       # Unit test suite for Verifier agent & ledger
    ├── test_verifier_comprehensive.py # Re-fetch, SHA-256 tamper, rounding, and 8+ flawed sentences
    ├── test_skeptic.py        # Unit test suite for Skeptic agent stress testing
    ├── test_pipeline.py       # Integration tests for run_research.py & correction round
    ├── test_knowledge.py      # Test suite for local knowledge base & evaluation queries
    └── test_data_layer.py     # Test suite for multi-source fallback & disk caching
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

## ⚡ Pipeline Orchestrator (`run_research.py`)

Upgrade 4 introduces the end-to-end autonomous research orchestrator that coordinates four stages:
$$\text{Analyst Agent} \longrightarrow \text{Verifier Agent (Audit \& Live Re-Fetch)} \longrightarrow [\text{Correction Round 1}] \longrightarrow \text{Skeptic Agent} \longrightarrow \text{Synthesized Dossier}$$

### How to Run:
```powershell
# Run Workflow 1 for US stock (Apple):
.\.venv\Scripts\python.exe run_research.py AAPL 1

# Run Workflow 1 for Non-US stock (Tata Consultancy Services, India):
.\.venv\Scripts\python.exe run_research.py TCS.NS 1
```

### Pipeline Execution Lifecycle:
1. **Analyst Agent (`agents/analyst.py`)**:
   - Executes the requested playbook workflow (e.g. Workflow 1: Single-stock deep dive).
   - Ingests audited regulatory filings (`tools/filing.py`, SEC EDGAR XBRL facts, NSE/BSE press releases) and live market quotes.
   - Computes all margins, growth rates, cash conversion, DCF, and reverse DCF implied growth via `tools/calc/`.
   - Records every metric and calculation into the cryptographic HMAC-signed `ProvenanceLedger`.
   - Tags qualitative claims with `[UNVERIFIED: model memory]` and analytical deductions with `[ANALYSIS]`.
2. **Verifier Agent & Correction Round (`agents/verifier.py`)**:
   - Audits the analyst draft under strict default-deny parsing.
   - Cross-checks figures against the ledger, tolerance limits, and independent live source re-fetch.
   - **Automated Correction Round**: If `total_wrong > 0`, the orchestrator immediately routes the discrepancy list back to the Analyst Agent for **one correction round**, repairing the figures before re-auditing.
3. **Skeptic Agent (`agents/skeptic.py`)**:
   - Executes adversarial stress-testing (Reverse DCF hurdle, -200 bps margin shock, +100 bps WACC shock, working capital divergence, liquidity buffer).
   - Generates the $3 \times 3$ valuation sensitivity matrix (Growth $\times$ WACC) and adversarial checklist.
4. **Final Synthesized Dossier (`/reports/TICKER_YYYY-MM-DD/final_report.md`)**:
   - **Top Section**: Verification results (Status, Confirmed figures, Wrong figures, Unverified flags, what could not be checked, headline reconciliations).
   - **Middle Section**: Analyst research report (Business overview, audited financial statements table with ledger citations, quality and valuation metrics).
   - **End Section**: Skeptic adversarial review (Thesis verdict, assumptions stress tests, sensitivity grid, bear case).

---

## 📚 Local Knowledge Base (`tools/knowledge.py`)

Upgrade 5 provides a local, free, persistent vector knowledge base powered by **ChromaDB** (`library/chroma_db/`).
It allows research agents to search primary corporate filings, earnings call transcripts, and analyst notes with full metadata preservation and citation tracing.

### Ingestion Commands:
```powershell
# Ingest all files dropped into /library/filings/, /library/transcripts/, and /library/notes/:
.\.venv\Scripts\python.exe tools/knowledge.py ingest-all

# Ingest a specific 10-K or filing:
.\.venv\Scripts\python.exe tools/knowledge.py ingest library/filings/AAPL_10K_FY2025.htm --type filing --ticker AAPL

# Check knowledge base status:
.\.venv\Scripts\python.exe tools/knowledge.py status
```

### Citation-Backed Search:
```powershell
# Search for specific queries with ticker filtering:
.\.venv\Scripts\python.exe tools/knowledge.py search "net sales breakdown Products and Services" --ticker AAPL --top-k 3
```

All results return formatted citations:
`[Citation: <ticker> | <document_type> | <filename> | <page_or_section> | Date: <date> | Source: <source_url>]`

### Standing Rule 12 (Knowledge Base Priority):
> **Rule 12**: Always check the local knowledge base (`/tools/knowledge.py`) before searching the web. Prefer ingested primary filings, transcripts, and verified notes.

---

## 🌐 Multi-Source Data Layer with Fallback & Caching (`tools/data_layer.py`)

Upgrade 6 provides an abstracted data access layer with multi-tier cascading fallback and disk caching:
$$\text{Local Cache (TTL)} \longrightarrow \text{Primary (SEC EDGAR / yfinance)} \longrightarrow \text{Backup 1 (Finnhub)} \longrightarrow \text{Backup 2 (FMP)} \longrightarrow \text{Backup 3 (Alpha Vantage)}$$

### Usage Commands:
```powershell
# Fetch quote with automatic fallback & provenance recording:
.\.venv\Scripts\python.exe tools/data_layer.py quote AAPL

# Fetch macroeconomic series with fallback (FRED / Treasury Yield proxies):
.\.venv\Scripts\python.exe tools/data_layer.py macro DGS10

# Display live free-tier limits:
.\.venv\Scripts\python.exe tools/data_layer.py limits

# Display regional market coverage and data gaps:
.\.venv\Scripts\python.exe tools/data_layer.py coverage
```

### Free-Tier API Limits & Strategy:
- **FRED**: 120 req/min, unlimited daily (Macro benchmark).
- **FMP**: 5 req/min, 250 req/day (5-year financials).
- **Finnhub**: 60 req/min (Real-time quotes & metrics).
- **Alpha Vantage**: 5 req/min, 25 req/day (Strict limit; caching mandatory).
- **yfinance**: ~2,000 req/hour (Primary zero-key global quotes).
- **SEC EDGAR**: 10 req/sec, unlimited daily (Primary audited US facts).

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

---

## 🚨 Regulatory Filing & Market Event Alerts Monitor (`/tools/alerts.py`)

Upgrade 7 monitors covered securities in `watchlist.txt` for:
- New SEC EDGAR filings (Forms 10-K, 10-Q, 8-K, Form 4) with accession tracking.
- Market price shocks exceeding $\pm 3\%$ daily move.
- Persists state in `/alerts/alerts_state.json` and emits markdown digests in `/alerts/alerts_YYYY-MM-DD.md`.

```powershell
.\.venv\Scripts\python.exe tools/alerts.py
```

---

## 📅 Scheduled Weekly Watchlist Briefing (`/tools/briefing.py`)

Upgrade 8 implements **Workflow 10** from `research_playbook_v2.md`:
- Multi-timeframe performance (1W, 1M, YTD) in local currency across US, UK, and Indian listings.
- Macroeconomic barometer (10Y US Treasury Yield, Brent Crude Oil, USD/INR FX).
- Automated thesis contradiction checks against `watchlist.txt`.
- Emits markdown dossiers in `/reports/briefing_YYYY-MM-DD.md`.

```powershell
.\.venv\Scripts\python.exe tools/briefing.py
```

---

## 📓 Investment Decision Journal & Portfolio Review (`/tools/journal.py`)

Upgrade 9 enforces institutional investment discipline:
- Tracks entry prices, target prices, downside stop-losses, core thesis, and invalidation catalysts in `/journal/journal.csv`.
- Generates individual decision post-mortems in `/journal/entries/`.
- Renders comprehensive portfolio decision review summaries in `/journal/portfolio_review.md`.

```powershell
.\.venv\Scripts\python.exe tools/journal.py
```

---

## 🧪 Quantitative Screening & Backtesting Sandbox (`/tools/backtest.py`)

Upgrade 10 implements **Workflow 9** (Fundamental Screener) and historical portfolio simulation:
- Multi-factor fundamental filter: Operating Margin $\ge 20\%$, Net Debt/Equity $\le 1.5$, FCF Yield $\ge 2.0\%$.
- Equal-weighted portfolio backtesting vs benchmark (SPY).
- Computes Sharpe ratio, Annualized Volatility, Maximum Drawdown, and Alpha.
- Emits simulation reports in `/backtests/backtest_YYYY-MM-DD.md`.

```powershell
.\.venv\Scripts\python.exe tools/backtest.py
```

