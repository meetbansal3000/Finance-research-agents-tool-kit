# Verification Audit Report
**Target Report:** `analyst_report.md`  
**Audit Timestamp:** 2026-10-06T23:01:48.944339  
**Overall Status:** **PASS WITH FLAGS (NOT RE-FETCHED)** (26 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (26)
- **[Line 12] [LEDGER_0001]**: AMAZON COM INC reported FY2025 total revenue of $716,924M [LEDGER_0001], representing a YoY revenue growth of 12.38% [LEDGER_0016].
  - *Verified Output:* `716924000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json (Accn: 0001018724-26-000004)
- **[Line 12] [LEDGER_0016]**: AMAZON COM INC reported FY2025 total revenue of $716,924M [LEDGER_0001], representing a YoY revenue growth of 12.38% [LEDGER_0016].
  - *Verified Output:* `12.377754683294695` via `tools.calc.yoy_growth`
  - *Source:* tools.calc.metrics.yoy_growth
- **[Line 13] [LEDGER_0003]**: Operating income was $79,975M [LEDGER_0003], resulting in an operating margin of 11.16% [LEDGER_0017].
  - *Verified Output:* `79975000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json (Accn: 0001018724-26-000004)
- **[Line 13] [LEDGER_0017]**: Operating income was $79,975M [LEDGER_0003], resulting in an operating margin of 11.16% [LEDGER_0017].
  - *Verified Output:* `11.155296795755199` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 14] [LEDGER_0004]**: Net income reached $77,670M [LEDGER_0004], delivering a net margin of 10.83% [LEDGER_0018].
  - *Verified Output:* `77670000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json (Accn: 0001018724-26-000004)
- **[Line 14] [LEDGER_0018]**: Net income reached $77,670M [LEDGER_0004], delivering a net margin of 10.83% [LEDGER_0018].
  - *Verified Output:* `10.83378433418326` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 15] [LEDGER_0005]**: Cash flow from operations was $139,514M [LEDGER_0005] and capital expenditures were $131,819M [LEDGER_0006].
  - *Verified Output:* `139514000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json (Accn: 0001018724-26-000004)
- **[Line 15] [LEDGER_0006]**: Cash flow from operations was $139,514M [LEDGER_0005] and capital expenditures were $131,819M [LEDGER_0006].
  - *Verified Output:* `131819000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json
- **[Line 16] [LEDGER_0019]**: Free cash flow was $7,695M [LEDGER_0019], yielding an FCF yield of 0.28% [LEDGER_0020].
  - *Verified Output:* `7695000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 16] [LEDGER_0020]**: Free cash flow was $7,695M [LEDGER_0019], yielding an FCF yield of 0.28% [LEDGER_0020].
  - *Verified Output:* `0.27835813717373514` via `tools.calc.fcf_yield`
  - *Source:* tools.calc.metrics.fcf_yield
- **[Line 17] [LEDGER_0007]**: Balance sheet cash and marketable securities totaled $123,029M [LEDGER_0007] against total debt of $68,396M [LEDGER_0008], resulting in a net debt of -$54,633M [LEDGER_0009].
  - *Verified Output:* `123029000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json
- **[Line 17] [LEDGER_0008]**: Balance sheet cash and marketable securities totaled $123,029M [LEDGER_0007] against total debt of $68,396M [LEDGER_0008], resulting in a net debt of -$54,633M [LEDGER_0009].
  - *Verified Output:* `68396000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json
- **[Line 17] [LEDGER_0009]**: Balance sheet cash and marketable securities totaled $123,029M [LEDGER_0007] against total debt of $68,396M [LEDGER_0008], resulting in a net debt of -$54,633M [LEDGER_0009].
  - *Verified Output:* `-54633000000.0` via `tools.calc.net_debt`
  - *Source:* Calculated: Total Debt - Liquid Assets
- **[Line 18] [LEDGER_0010]**: Current market price trades at $256.29 USD [LEDGER_0010].
  - *Verified Output:* `256.29` via `yfinance.quote`
  - *Source:* Yahoo Finance Market Quote
- **[Line 19] [LEDGER_0021]**: Baseline DCF fair value estimate is $20.49 [LEDGER_0021].
  - *Verified Output:* `20.49212044818143` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 20] [LEDGER_0022]**: Reverse DCF model indicates the current market price implies a 5-year FCF CAGR of 94.08% [LEDGER_0022].
  - *Verified Output:* `94.08490061759949` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 28] [LEDGER_0001]**: | Total Net Sales | $716,924M | [LEDGER_0001] | Primary Audited Filing |
  - *Verified Output:* `716924000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json (Accn: 0001018724-26-000004)
- **[Line 29] [LEDGER_0003]**: | Operating Income | $79,975M | [LEDGER_0003] | Primary Audited Filing |
  - *Verified Output:* `79975000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json (Accn: 0001018724-26-000004)
- **[Line 30] [LEDGER_0004]**: | Net Income | $77,670M | [LEDGER_0004] | Primary Audited Filing |
  - *Verified Output:* `77670000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json (Accn: 0001018724-26-000004)
- **[Line 31] [LEDGER_0005]**: | Operating Cash Flow | $139,514M | [LEDGER_0005] | Primary Audited Filing |
  - *Verified Output:* `139514000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json (Accn: 0001018724-26-000004)
- **[Line 32] [LEDGER_0006]**: | Capital Expenditures | $131,819M | [LEDGER_0006] | Primary Audited Filing |
  - *Verified Output:* `131819000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json
- **[Line 33] [LEDGER_0019]**: | Free Cash Flow | $7,695M | [LEDGER_0019] | Calculated: OCF - Capex |
  - *Verified Output:* `7695000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 34] [LEDGER_0007]**: | Total Cash & Marketable Securities | $123,029M | [LEDGER_0007] | Audited Balance Sheet |
  - *Verified Output:* `123029000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json
- **[Line 35] [LEDGER_0008]**: | Total Debt Obligations | $68,396M | [LEDGER_0008] | Audited Balance Sheet |
  - *Verified Output:* `68396000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001018724.json
- **[Line 36] [LEDGER_0009]**: | Net Debt Position | -$54,633M | [LEDGER_0009] | Calculated: Total Debt - Liquid Assets |
  - *Verified Output:* `-54633000000.0` via `tools.calc.net_debt`
  - *Source:* Calculated: Total Debt - Liquid Assets
- **[Line 44] [LEDGER_0022]**: [ANALYSIS] The implied growth rate of 94.08% [LEDGER_0022] exceeds the baseline growth assumption and reflects a premium multiple.
  - *Verified Output:* `94.08490061759949` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 42] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] AMAZON COM INC maintains competitive market positioning across its core operating business lines.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 43] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Multi-year customer relationships and global distribution support continuous operations.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*