# Verification Audit Report
**Target Report:** `aapl_research_report.md`  
**Audit Timestamp:** 2026-10-06T15:08:18.676663  
**Overall Status:** **PASS WITH FLAGS** (20 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (20)
- **[Line 10] [LEDGER_0001]**: Apple reported FY2025 total revenue of $416,161M [LEDGER_0001], representing a YoY revenue growth of 6.43% [LEDGER_0008].
  - *Verified Output:* `416161000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 10] [LEDGER_0008]**: Apple reported FY2025 total revenue of $416,161M [LEDGER_0001], representing a YoY revenue growth of 6.43% [LEDGER_0008].
  - *Verified Output:* `6.425511782832739` via `tools.calc.yoy_growth`
  - *Source:* tools.calc.metrics.yoy_growth
- **[Line 11] [LEDGER_0003]**: Operating income was $133,050M [LEDGER_0003], resulting in an operating margin of 31.97% [LEDGER_0009].
  - *Verified Output:* `133050000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 11] [LEDGER_0009]**: Operating income was $133,050M [LEDGER_0003], resulting in an operating margin of 31.97% [LEDGER_0009].
  - *Verified Output:* `31.970799762591884` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 12] [LEDGER_0004]**: Net income reached $112,010M [LEDGER_0004], delivering a net margin of 26.92% [LEDGER_0010].
  - *Verified Output:* `112010000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 12] [LEDGER_0010]**: Net income reached $112,010M [LEDGER_0004], delivering a net margin of 26.92% [LEDGER_0010].
  - *Verified Output:* `26.91506412181824` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 13] [LEDGER_0005]**: Cash flow from operations was $111,482M [LEDGER_0005] and capital expenditures were $12,715M [LEDGER_0006].
  - *Verified Output:* `111482000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 13] [LEDGER_0006]**: Cash flow from operations was $111,482M [LEDGER_0005] and capital expenditures were $12,715M [LEDGER_0006].
  - *Verified Output:* `12715000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 14] [LEDGER_0011]**: Free cash flow was $98,767M [LEDGER_0011], yielding an FCF yield of 2.03% [LEDGER_0012].
  - *Verified Output:* `98767000000` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 14] [LEDGER_0012]**: Free cash flow was $98,767M [LEDGER_0011], yielding an FCF yield of 2.03% [LEDGER_0012].
  - *Verified Output:* `2.0329110145312077` via `tools.calc.fcf_yield`
  - *Source:* tools.calc.metrics.fcf_yield
- **[Line 15] [LEDGER_0007]**: Current market price trades at $332.90 USD [LEDGER_0007].
  - *Verified Output:* `332.9` via `yfinance.quote`
  - *Source:* Yahoo Finance Market Quote
- **[Line 16] [LEDGER_0013]**: Baseline DCF fair value estimate is $139.57 [LEDGER_0013].
  - *Verified Output:* `139.56924608382886` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 17] [LEDGER_0014]**: Reverse DCF model indicates the current market price implies a 5-year FCF CAGR of 28.97% [LEDGER_0014].
  - *Verified Output:* `28.97093892097473` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 25] [LEDGER_0001]**: | Total Net Sales | $416,161M | [LEDGER_0001] | SEC EDGAR 10-K (Accn: 0000320193-25-000079) |
  - *Verified Output:* `416161000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 26] [LEDGER_0003]**: | Operating Income | $133,050M | [LEDGER_0003] | SEC EDGAR 10-K (Accn: 0000320193-25-000079) |
  - *Verified Output:* `133050000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 27] [LEDGER_0004]**: | Net Income | $112,010M | [LEDGER_0004] | SEC EDGAR 10-K (Accn: 0000320193-25-000079) |
  - *Verified Output:* `112010000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 28] [LEDGER_0005]**: | Operating Cash Flow | $111,482M | [LEDGER_0005] | SEC EDGAR 10-K (Accn: 0000320193-25-000079) |
  - *Verified Output:* `111482000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 29] [LEDGER_0006]**: | Capital Expenditures | $12,715M | [LEDGER_0006] | SEC EDGAR 10-K (Accn: 0000320193-25-000079) |
  - *Verified Output:* `12715000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json (Accn: 0000320193-25-000079)
- **[Line 30] [LEDGER_0011]**: | Free Cash Flow | $98,767M | [LEDGER_0011] | Calculated: OCF - Capex |
  - *Verified Output:* `98767000000` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 38] [LEDGER_0014]**: [ANALYSIS] The implied growth rate of 28.97% [LEDGER_0014] exceeds the baseline growth assumption and reflects a premium multiple.
  - *Verified Output:* `28.97093892097473` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 36] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Apple maintains strong ecosystem retention across hardware devices and subscription services.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 37] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Installed base expansion supports recurring high-margin services revenue.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*