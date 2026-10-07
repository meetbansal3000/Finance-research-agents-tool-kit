# AGENTS.md - Antigravity & OpenAI Codex Shared Directives

This document defines the architecture, data integrity standards, execution guidelines, and tool protocols for both **Google Antigravity** and **OpenAI Codex CLI** operating within the `finance agents for research` repository.

---

## 1. Project Mission & Core Rules
This codebase is an institutional-grade autonomous equity research system designed for fundamental security analysis, financial statement extraction, valuation, and thesis monitoring.

### ⚠️ Cardinal Rule: Zero Fabrication & Non-Negotiable Provenance
1. **Never fabricate or estimate financial figures.** All balance sheet, income statement, and cash flow numbers must be sourced directly from:
   - Primary SEC EDGAR 10-K / 10-Q filings (for US filers)
   - SEC Form 20-F filings under `ifrs-full` taxonomy (for foreign private issuers like TSM, BABA, ASML)
   - Audited exchange press releases / ESEF reports (for international filers like TCS.NS)
2. **Period Integrity:** Every metric registered must carry its explicit `period_end` (e.g. `2025-09-27`), `fiscal_year` (e.g. `FY2025`), and accession number. Prior-period figures cannot be silently substituted for current periods.
3. **Immutable Provenance Ledger:** Every extracted figure must be registered in [`tools/ledger.py`](tools/ledger.py) generating a deterministic `[LEDGER_XXXX]` ID.

---

## 2. Multi-Agent Topology
The system operates as a committee of specialized agents:
- **AnalystAgent (`agents/analyst.py`):** Fetches primary filing facts, compiles financial statements, computes FCF, Net Debt, and valuation metrics.
- **VerifierAgent (`agents/verifier.py`):** Independently re-fetches numbers through a distinct code path / document view. Reconciles facts against stated periods. Flags discrepancies.
- **SkepticAgent (`agents/skeptic.py`):** Red-team auditor. Checks customer concentration risk, working capital divergence, cash-flow quality, and inventory buildup.
- **NoteExtractorAgent (`agents/note_extractor.py`):** Parses unstructured HTML disclosures (e.g., Note 19 customer concentration) using regex and textual NLP.
- **CodexBridge (`tools/codex_bridge.py`):** Connects Antigravity and OpenAI Codex CLI for cross-agent code reviews, dual verification, and automated audits.

---

## 3. Data Layer & API Quota Management
All external API requests must route through [`tools/data_layer.py`](tools/data_layer.py):
- **DiskCache:** Local JSON caching in `library/cache/` with 30-minute TTL for quotes and 24-hour TTL for financials.
- **TokenBucketRateLimiter:** Mandatory inter-request delay enforcement (`yfinance`: 0.15s, `SEC EDGAR`: 0.10s, `Finnhub`: 1.05s, `FMP`: 12.0s, `Alpha Vantage`: 15.0s).
- **Alpha Vantage Quota Guard:** Strictly monitors daily calls on disk (`alpha_vantage_daily_quota.json`) to prevent exceeding the 25 calls/day free limit.
- **Batch Processing:** Multi-ticker universe screening must use `get_quotes_batch()` with `fast_info` acceleration.

---

## 4. Environment & Testing Guidelines
- **Python Virtual Environment:** `.\.venv\Scripts\python.exe`
- **Testing:** Always run tests via `.\.venv\Scripts\pytest.exe`. All 58+ unit and integration tests must pass.
- **Interactive UI:** Launch Streamlit dashboard via `.\.venv\Scripts\streamlit.exe run dashboard.py`.
- **Scheduled Briefings:** Scheduled jobs run `scripts/weekly_briefing.py` and `tools/alerts.py`.
