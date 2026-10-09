# AGENTS.md - Antigravity & OpenAI Codex Shared Directives

This document defines the architecture, data integrity standards, execution guidelines, agent roles, and tool protocols for both **Google Antigravity** and **OpenAI Codex CLI** operating within the `Finance Research Agents Tool-Kit` repository.

---

## 1. Project Mission & Core Rules
This codebase is an institutional-grade autonomous equity research system designed for fundamental security analysis, financial statement extraction, mathematical optimization, and valuation monitoring.

### ⚠️ Cardinal Rule: Zero Fabrication & Non-Negotiable Provenance
1. **Never fabricate or estimate financial figures.** All balance sheet, income statement, and cash flow numbers must be sourced directly from:
   - Primary SEC EDGAR 10-K / 10-Q filings (for US filers)
   - SEC Form 20-F filings under `ifrs-full` taxonomy (for foreign private issuers like TSM, BABA, ASML)
   - Audited exchange press releases / ESEF reports (for international filers like TCS.NS)
2. **Period Integrity:** Every metric registered must carry its explicit `period_end` (e.g. `2025-09-27`), `fiscal_year` (e.g. `FY2025`), and accession number. Prior-period figures cannot be silently substituted for current periods.
3. **Immutable Provenance Ledger:** Every extracted figure, calculation, and model output must be registered in [`tools/ledger.py`](tools/ledger.py) generating a deterministic `[LEDGER_XXXX]` ID with an HMAC-SHA256 signature.
4. **Security & Credentials:** Never commit API keys (NVIDIA, OpenAI, SEC, Finnhub) to git. All credentials reside strictly in untracked local `.env`.

---

## 2. Multi-Agent Topology & Committee Structure
The system operates as an autonomous committee of specialized agents:
- **AnalystAgent (`agents/analyst.py`, `agents/analyst.md`):** Extracts primary filing facts, compiles financial statements, computes analytical DCF, reverse DCF, and capital return yields.
- **IndependentVerifier (`agents/verifier.py`, `agents/verifier.md`):** Independently re-fetches numbers through a distinct code path / document view. Reconciles facts against stated periods within 0.5 unit tolerance. Enforces 4-tier classification (`PASSED`, `IMPRECISION`, `FACTUAL_ERROR`, `UNVERIFIED`).
- **SkepticAgent (`agents/skeptic.py`, `agents/skeptic.md`):** Red-team auditor. Checks customer concentration risk, working capital divergence, cash-flow quality, inventory buildup, and WACC sensitivity.
- **NoteExtractorAgent (`agents/note_extractor.py`, `agents/note_extractor.md`):** Parses unstructured HTML footnotes (e.g. Note 19 Customer Concentration >10% revenue) using regex and textual normalization.
- **NvidiaResearchAgent (`agents/nvidia_agent.py`, `agents/nvidia_agent.md`):** High-throughput reasoning agent using NVIDIA NIM LLMs (Nemotron 550B, Llama 3.3, Mistral Large, DeepSeek R1) with multi-key pooling and offline deterministic fallbacks.
- **ResearchCommittee (`agents/committee.py`):** Orchestrator coordinating the complete committee workflow from ingestion to final audited memorandum.
- **AlertMonitor (`tools/alert_monitor.py`):** Real-time watchlist monitor for price breakout ($\pm 5\%$), SEC 8-K/10-Q disclosures, and margin shocks.
- **WeeklyBriefing (`tools/weekly_briefing.py`):** Compiles weekly institutional digests across watchlist assets and earnings updates.
- **DecisionJournal (`tools/decision_journal.py`):** Records investment committee decisions with cryptographic HMAC hash and review dates.
- **BacktestSandbox (`tools/backtest.py`):** Multi-factor screening and quantitative backtesting engine featuring cuOpt QP portfolio variance minimization vs SPY.
- **CodexBridge (`tools/codex_bridge.py`):** Connects Antigravity and OpenAI Codex CLI for cross-agent code reviews, dual verification, and automated audits.
- **RStudioBridge (`tools/r_bridge.py`, `r_studio/agent_bridge.R`):** Connects Python agents to native R 4.6.1 for Monte Carlo DCF simulations, portfolio QP, and CVRP supply chain logistics.

---

## 3. NVIDIA Optimization & Simulation Suite
Three specialized skills provide GPU-grade mathematical and algorithmic modeling:
1. **`cuopt-numerical-optimization-formulation` (`tools/calc/portfolio_opt.py`):**
   - Implements `PortfolioQPOptimizer` for Markowitz mean-variance and Global Minimum Variance portfolio allocation.
   - Enforces $Q \succeq 0$ positive semi-definiteness and extracts dual sensitivity multipliers.
2. **`cuopt-routing-api-python` (`tools/calc/supply_chain_opt.py`):**
   - Implements `SupplyChainLogisticsOptimizer` for Capacitated Vehicle Routing Problems (CVRP).
   - Computes delivery cost per unit, fleet utilization, and gross margin elasticity under fuel shocks (+10%, +20%).
3. **`tilegym-cutile-autotuning` (`tools/calc/gpu_autotune_sim.py`):**
   - Implements `FinancialKernelAutotuner` following the tune-once/cache/launch pattern with occupancy sweep `[1, 2, 4, 8]`.
   - Accelerates Monte Carlo Cholesky path simulations and covariance estimations.

---

## 4. Antigravity Skill Discovery Scopes
Antigravity automatically discovers skills and agents across two layers:
1. **Workspace Scope:** Looks for `.agents/skills/` and `AGENTS.md` inside the currently opened workspace directory:
   - Location: `D:\AI-Workspace\finance agents for research\.agents\skills\`
   - To activate workspace scope in Antigravity IDE: **File > Open Folder** and select `D:\AI-Workspace\finance agents for research`.
2. **Global Scope:** Located in the user's Antigravity configuration directory:
   - Location: `C:\Users\HP\.gemini\config\skills\`
   - All 3 NVIDIA skills (`cuopt-numerical-optimization-formulation`, `cuopt-routing-api-python`, `tilegym-cutile-autotuning`) are duplicated here, ensuring global availability regardless of active workspace.

---

## 5. Environment & Verification Guidelines
- **Python Virtual Environment:** `.\.venv\Scripts\python.exe`
- **Testing:** Always run tests via `.\.venv\Scripts\pytest.exe`. All **89 / 89 tests must pass (100%)**.
- **Interactive UI:** Launch Streamlit dashboard via `.\.venv\Scripts\streamlit.exe run dashboard.py`.
- **Master Excel Catalog:** Generated at [`agents_and_skills_catalog.xlsx`](agents_and_skills_catalog.xlsx) via `python scripts/generate_agents_skills_catalog.py`.
- **Git Version Control:** Main branch synced with `origin/main` (Release tag: `v1.4.0`).

## 6. OpenAccountant Finance Playbooks
- The 44 OpenAccountant playbooks are installed under `.agents/skills/` and pinned in `skills-lock.json`. Workspace Codex agents can discover them when a task matches a playbook.
- Treat playbooks as workflow guidance, not as financial evidence or executable Python tools. Continue to enforce the source, period-integrity, and provenance rules above.
- Do not claim Wilson transaction search, bookkeeping writes, bank synchronization, or Plaid access; this repository does not configure those services. Use the playbook's manual/exported-data path only when the user supplies suitable data.
- Keep the equity research committee's Analyst → Verifier → Skeptic flow unchanged unless a separately scoped, auditable runtime integration is implemented.
- The Streamlit Finance playbooks page is a read-only browser for the installed guides. It must identify unavailable integrations and must not imply that merely opening a guide ran its workflow.
