# Verification Audit Report
**Target Report:** `analyst_report.md`  
**Audit Timestamp:** 2026-10-06T17:15:43.313007  
**Overall Status:** **PASS WITH FLAGS** (26 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (26)
- **[Line 12] [LEDGER_0012]**: Microsoft Corporation reported FY2026 total revenue of $331,839M [LEDGER_0012], representing a YoY revenue growth of 17.79% [LEDGER_0019].
  - *Verified Output:* `331839000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660)
- **[Line 12] [LEDGER_0019]**: Microsoft Corporation reported FY2026 total revenue of $331,839M [LEDGER_0012], representing a YoY revenue growth of 17.79% [LEDGER_0019].
  - *Verified Output:* `17.78868679984666` via `tools.calc.yoy_growth`
  - *Source:* tools.calc.metrics.yoy_growth
- **[Line 13] [LEDGER_0014]**: Operating income was $155,237M [LEDGER_0014], resulting in an operating margin of 46.78% [LEDGER_0020].
  - *Verified Output:* `155237000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660)
- **[Line 13] [LEDGER_0020]**: Operating income was $155,237M [LEDGER_0014], resulting in an operating margin of 46.78% [LEDGER_0020].
  - *Verified Output:* `46.780818408927225` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 14] [LEDGER_0015]**: Net income reached $133,749M [LEDGER_0015], delivering a net margin of 40.31% [LEDGER_0021].
  - *Verified Output:* `133749000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660)
- **[Line 14] [LEDGER_0021]**: Net income reached $133,749M [LEDGER_0015], delivering a net margin of 40.31% [LEDGER_0021].
  - *Verified Output:* `40.30538905915218` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 15] [LEDGER_0016]**: Cash flow from operations was $182,935M [LEDGER_0016] and capital expenditures were $115,948M [LEDGER_0017].
  - *Verified Output:* `182935000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660)
- **[Line 15] [LEDGER_0017]**: Cash flow from operations was $182,935M [LEDGER_0016] and capital expenditures were $115,948M [LEDGER_0017].
  - *Verified Output:* `115948000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660)
- **[Line 16] [LEDGER_0022]**: Free cash flow was $66,987M [LEDGER_0022], yielding an FCF yield of 1.69% [LEDGER_0023].
  - *Verified Output:* `66987000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 16] [LEDGER_0023]**: Free cash flow was $66,987M [LEDGER_0022], yielding an FCF yield of 1.69% [LEDGER_0023].
  - *Verified Output:* `1.6946228775565526` via `tools.calc.fcf_yield`
  - *Source:* tools.calc.metrics.fcf_yield
- **[Line 17] [LEDGER_0003]**: Balance sheet cash and marketable securities totaled $76,843M [LEDGER_0003] against total debt of $40,294M [LEDGER_0006], resulting in a net debt of -$36,549M [LEDGER_0007].
  - *Verified Output:* `76843000000.0` via `tools.filing.extract_metric`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660, Consolidated Balance Sheets, Item 8 (Total Liquid Assets))
- **[Line 17] [LEDGER_0006]**: Balance sheet cash and marketable securities totaled $76,843M [LEDGER_0003] against total debt of $40,294M [LEDGER_0006], resulting in a net debt of -$36,549M [LEDGER_0007].
  - *Verified Output:* `40294000000.0` via `tools.filing.extract_metric`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660, Consolidated Balance Sheets, Item 8)
- **[Line 17] [LEDGER_0007]**: Balance sheet cash and marketable securities totaled $76,843M [LEDGER_0003] against total debt of $40,294M [LEDGER_0006], resulting in a net debt of -$36,549M [LEDGER_0007].
  - *Verified Output:* `-36549000000.0` via `tools.filing.extract_metric`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660, Calculated: Total Debt ($40,294M) - Liquid Assets ($76,843M))
- **[Line 18] [LEDGER_0018]**: Current market price trades at $532.34 USD [LEDGER_0018].
  - *Verified Output:* `532.34` via `yfinance.quote`
  - *Source:* Yahoo Finance Market Quote
- **[Line 19] [LEDGER_0024]**: Baseline DCF fair value estimate is $190.97 [LEDGER_0024].
  - *Verified Output:* `190.96780421594804` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 20] [LEDGER_0025]**: Reverse DCF model indicates the current market price implies a 5-year FCF CAGR of 33.78% [LEDGER_0025].
  - *Verified Output:* `33.776384592056274` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 28] [LEDGER_0012]**: | Total Net Sales | $331,839M | [LEDGER_0012] | Primary Audited Filing |
  - *Verified Output:* `331839000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660)
- **[Line 29] [LEDGER_0014]**: | Operating Income | $155,237M | [LEDGER_0014] | Primary Audited Filing |
  - *Verified Output:* `155237000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660)
- **[Line 30] [LEDGER_0015]**: | Net Income | $133,749M | [LEDGER_0015] | Primary Audited Filing |
  - *Verified Output:* `133749000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660)
- **[Line 31] [LEDGER_0016]**: | Operating Cash Flow | $182,935M | [LEDGER_0016] | Primary Audited Filing |
  - *Verified Output:* `182935000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660)
- **[Line 32] [LEDGER_0017]**: | Capital Expenditures | $115,948M | [LEDGER_0017] | Primary Audited Filing |
  - *Verified Output:* `115948000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660)
- **[Line 33] [LEDGER_0022]**: | Free Cash Flow | $66,987M | [LEDGER_0022] | Calculated: OCF - Capex |
  - *Verified Output:* `66987000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 34] [LEDGER_0003]**: | Total Cash & Marketable Securities | $76,843M | [LEDGER_0003] | Audited Balance Sheet |
  - *Verified Output:* `76843000000.0` via `tools.filing.extract_metric`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660, Consolidated Balance Sheets, Item 8 (Total Liquid Assets))
- **[Line 35] [LEDGER_0006]**: | Total Debt Obligations | $40,294M | [LEDGER_0006] | Audited Balance Sheet |
  - *Verified Output:* `40294000000.0` via `tools.filing.extract_metric`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660, Consolidated Balance Sheets, Item 8)
- **[Line 36] [LEDGER_0007]**: | Net Debt Position | -$36,549M | [LEDGER_0007] | Calculated: Total Debt - Liquid Assets |
  - *Verified Output:* `-36549000000.0` via `tools.filing.extract_metric`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json (Accn: 0001193125-26-323660, Calculated: Total Debt ($40,294M) - Liquid Assets ($76,843M))
- **[Line 44] [LEDGER_0025]**: [ANALYSIS] The implied growth rate of 33.78% [LEDGER_0025] exceeds the baseline growth assumption and reflects a premium multiple.
  - *Verified Output:* `33.776384592056274` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 42] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Microsoft commands global enterprise leadership across cloud computing, productivity suites, and developer platforms.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 43] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Expanding enterprise cloud migrations and AI workload adoption support recurring enterprise software margins.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*