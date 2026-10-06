# Standing Rules for Financial and Market Research

All research tasks and agent behaviors MUST strictly follow the master rules in [research_playbook_v2.md](file:///D:/AI-Workspace/finance%20agents%20for%20research/research_playbook_v2.md):

1. **Source Every Number**: Provide the exact filing URL, accession number, form type (10-K, 10-Q, 8-K, 20-F), or data tool endpoint + timestamp. No source = no number.
2. **Accounting Standard & Currency**: Explicitly state accounting standard (US GAAP, IFRS, J-GAAP, Ind AS, HKFRS, CAS), reporting currency, and fiscal year-end for every company. Never compare across companies without noting differences.
3. **Show Arithmetic**: Provide explicit mathematical calculations for any ratio or growth rate. Say which period each figure covers.
4. **Primary Filings First**: Prioritize the company's own filings over third-party aggregators. If they disagree, report both.
5. **Timestamped Price Data**: Label market price data with timestamp and exchange source. Note if delayed.
6. **Fact vs. Interpretation**: Separate documented facts from analytical interpretation. Mark interpretation clearly.
7. **Explicit Uncertainty**: State what could not be found or verified. Never fill gaps with guesses.
8. **Balanced Perspective**: Impartial research only (no buy/sell calls). Present bull case, bear case, and 3 key monitoring catalysts.
9. **Standardized Reports**: Save research reports to `reports/TICKER_task_YYYY-MM-DD.md`.
10. **Sandbox Confinement**: Work only inside this project folder. Ask before installing anything new.
11. **Calculation Toolkit Enforcement**: Never perform mental or rough arithmetic. Always call the deterministic calculation toolkit in `/tools/calc/` (`yoy_growth`, `cagr`, `margin`, `roic`, `roe`, `free_cash_flow`, `fcf_yield`, `net_debt_to_ebitda`, `interest_coverage`, `cash_conversion`, `enterprise_value`, `ev_multiples`, `dcf`, `reverse_dcf`, `convert_currency`).
12. **Knowledge Base Priority**: Check the local knowledge base (`/tools/knowledge.py`) before searching the web. Search existing local filings, transcripts, and notes before making external calls.
