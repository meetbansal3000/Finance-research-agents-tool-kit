# Verification Audit Report
**Target Report:** `analyst_report.md`  
**Audit Timestamp:** 2026-10-06T16:11:30.272492  
**Overall Status:** **PASS WITH FLAGS** (26 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (26)
- **[Line 12] [LEDGER_0012]**: Apple Inc. reported FY2025 total revenue of $416,161M [LEDGER_0012], representing a YoY revenue growth of 6.43% [LEDGER_0019].
  - *Verified Output:* `416161000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 12] [LEDGER_0019]**: Apple Inc. reported FY2025 total revenue of $416,161M [LEDGER_0012], representing a YoY revenue growth of 6.43% [LEDGER_0019].
  - *Verified Output:* `6.425511782832739` via `tools.calc.yoy_growth`
  - *Source:* tools.calc.metrics.yoy_growth
- **[Line 13] [LEDGER_0014]**: Operating income was $133,050M [LEDGER_0014], resulting in an operating margin of 31.97% [LEDGER_0020].
  - *Verified Output:* `133050000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 13] [LEDGER_0020]**: Operating income was $133,050M [LEDGER_0014], resulting in an operating margin of 31.97% [LEDGER_0020].
  - *Verified Output:* `31.970799762591884` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 14] [LEDGER_0015]**: Net income reached $112,010M [LEDGER_0015], delivering a net margin of 26.92% [LEDGER_0021].
  - *Verified Output:* `112010000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 14] [LEDGER_0021]**: Net income reached $112,010M [LEDGER_0015], delivering a net margin of 26.92% [LEDGER_0021].
  - *Verified Output:* `26.91506412181824` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 15] [LEDGER_0016]**: Cash flow from operations was $111,482M [LEDGER_0016] and capital expenditures were $12,715M [LEDGER_0017].
  - *Verified Output:* `111482000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 15] [LEDGER_0017]**: Cash flow from operations was $111,482M [LEDGER_0016] and capital expenditures were $12,715M [LEDGER_0017].
  - *Verified Output:* `12715000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 16] [LEDGER_0022]**: Free cash flow was $98,767M [LEDGER_0022], yielding an FCF yield of 2.03% [LEDGER_0023].
  - *Verified Output:* `98767000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 16] [LEDGER_0023]**: Free cash flow was $98,767M [LEDGER_0022], yielding an FCF yield of 2.03% [LEDGER_0023].
  - *Verified Output:* `2.0332163939835937` via `tools.calc.fcf_yield`
  - *Source:* tools.calc.metrics.fcf_yield
- **[Line 17] [LEDGER_0004]**: Balance sheet cash and marketable securities totaled $138,638M [LEDGER_0004] against total debt of $101,650M [LEDGER_0006], resulting in a net debt of -$36,988M [LEDGER_0007].
  - *Verified Output:* `138638000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm (Consolidated Balance Sheets, Item 8 (Total Liquid Assets))
- **[Line 17] [LEDGER_0006]**: Balance sheet cash and marketable securities totaled $138,638M [LEDGER_0004] against total debt of $101,650M [LEDGER_0006], resulting in a net debt of -$36,988M [LEDGER_0007].
  - *Verified Output:* `101650000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm (Consolidated Balance Sheets, Item 8)
- **[Line 17] [LEDGER_0007]**: Balance sheet cash and marketable securities totaled $138,638M [LEDGER_0004] against total debt of $101,650M [LEDGER_0006], resulting in a net debt of -$36,988M [LEDGER_0007].
  - *Verified Output:* `-36988000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm (Calculated: Total Debt ($101,650M) - Liquid Assets ($138,638M))
- **[Line 18] [LEDGER_0018]**: Current market price trades at $332.85 USD [LEDGER_0018].
  - *Verified Output:* `332.85` via `yfinance.quote`
  - *Source:* Yahoo Finance Market Quote
- **[Line 19] [LEDGER_0024]**: Baseline DCF fair value estimate is $142.10 [LEDGER_0024].
  - *Verified Output:* `142.10368104351826` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 20] [LEDGER_0025]**: Reverse DCF model indicates the current market price implies a 5-year FCF CAGR of 28.76% [LEDGER_0025].
  - *Verified Output:* `28.75761389732361` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 28] [LEDGER_0012]**: | Total Net Sales | $416,161M | [LEDGER_0012] | Primary Audited Filing |
  - *Verified Output:* `416161000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 29] [LEDGER_0014]**: | Operating Income | $133,050M | [LEDGER_0014] | Primary Audited Filing |
  - *Verified Output:* `133050000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 30] [LEDGER_0015]**: | Net Income | $112,010M | [LEDGER_0015] | Primary Audited Filing |
  - *Verified Output:* `112010000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 31] [LEDGER_0016]**: | Operating Cash Flow | $111,482M | [LEDGER_0016] | Primary Audited Filing |
  - *Verified Output:* `111482000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 32] [LEDGER_0017]**: | Capital Expenditures | $12,715M | [LEDGER_0017] | Primary Audited Filing |
  - *Verified Output:* `12715000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 33] [LEDGER_0022]**: | Free Cash Flow | $98,767M | [LEDGER_0022] | Calculated: OCF - Capex |
  - *Verified Output:* `98767000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 34] [LEDGER_0004]**: | Total Cash & Marketable Securities | $138,638M | [LEDGER_0004] | Audited Balance Sheet |
  - *Verified Output:* `138638000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm (Consolidated Balance Sheets, Item 8 (Total Liquid Assets))
- **[Line 35] [LEDGER_0006]**: | Total Debt Obligations | $101,650M | [LEDGER_0006] | Audited Balance Sheet |
  - *Verified Output:* `101650000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm (Consolidated Balance Sheets, Item 8)
- **[Line 36] [LEDGER_0007]**: | Net Debt Position | -$36,988M | [LEDGER_0007] | Calculated: Total Debt - Liquid Assets |
  - *Verified Output:* `-36988000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm (Calculated: Total Debt ($101,650M) - Liquid Assets ($138,638M))
- **[Line 44] [LEDGER_0025]**: [ANALYSIS] The implied growth rate of 28.76% [LEDGER_0025] exceeds the baseline growth assumption and reflects a premium multiple.
  - *Verified Output:* `28.75761389732361` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 42] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Apple maintains strong ecosystem retention across hardware devices and subscription services.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 43] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Installed base expansion supports recurring high-margin services revenue.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*