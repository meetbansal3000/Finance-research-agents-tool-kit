# Verification Audit Report
**Target Report:** `analyst_report.md`  
**Audit Timestamp:** 2026-10-06T21:56:48.801632  
**Overall Status:** **PASS WITH FLAGS (NOT RE-FETCHED)** (26 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (26)
- **[Line 12] [LEDGER_0001]**: NVIDIA CORP reported FY2026 total revenue of $215,938M [LEDGER_0001], representing a YoY revenue growth of 65.47% [LEDGER_0016].
  - *Verified Output:* `215938000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json (Accn: 0001045810-26-000021)
- **[Line 12] [LEDGER_0016]**: NVIDIA CORP reported FY2026 total revenue of $215,938M [LEDGER_0001], representing a YoY revenue growth of 65.47% [LEDGER_0016].
  - *Verified Output:* `65.4735357900948` via `tools.calc.yoy_growth`
  - *Source:* tools.calc.metrics.yoy_growth
- **[Line 13] [LEDGER_0003]**: Operating income was $130,387M [LEDGER_0003], resulting in an operating margin of 60.38% [LEDGER_0017].
  - *Verified Output:* `130387000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json (Accn: 0001045810-26-000021)
- **[Line 13] [LEDGER_0017]**: Operating income was $130,387M [LEDGER_0003], resulting in an operating margin of 60.38% [LEDGER_0017].
  - *Verified Output:* `60.38168363141272` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 14] [LEDGER_0004]**: Net income reached $120,067M [LEDGER_0004], delivering a net margin of 55.60% [LEDGER_0018].
  - *Verified Output:* `120067000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json (Accn: 0001045810-26-000021)
- **[Line 14] [LEDGER_0018]**: Net income reached $120,067M [LEDGER_0004], delivering a net margin of 55.60% [LEDGER_0018].
  - *Verified Output:* `55.60253406070261` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 15] [LEDGER_0005]**: Cash flow from operations was $102,718M [LEDGER_0005] and capital expenditures were $6,042M [LEDGER_0006].
  - *Verified Output:* `102718000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json (Accn: 0001045810-26-000021)
- **[Line 15] [LEDGER_0006]**: Cash flow from operations was $102,718M [LEDGER_0005] and capital expenditures were $6,042M [LEDGER_0006].
  - *Verified Output:* `6042000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json
- **[Line 16] [LEDGER_0019]**: Free cash flow was $96,676M [LEDGER_0019], yielding an FCF yield of 1.67% [LEDGER_0020].
  - *Verified Output:* `96676000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 16] [LEDGER_0020]**: Free cash flow was $96,676M [LEDGER_0019], yielding an FCF yield of 1.67% [LEDGER_0020].
  - *Verified Output:* `1.67348451139158` via `tools.calc.fcf_yield`
  - *Source:* tools.calc.metrics.fcf_yield
- **[Line 17] [LEDGER_0007]**: Balance sheet cash and marketable securities totaled $10,605M [LEDGER_0007] against total debt of $8,468M [LEDGER_0008], resulting in a net debt of -$2,137M [LEDGER_0009].
  - *Verified Output:* `10605000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json
- **[Line 17] [LEDGER_0008]**: Balance sheet cash and marketable securities totaled $10,605M [LEDGER_0007] against total debt of $8,468M [LEDGER_0008], resulting in a net debt of -$2,137M [LEDGER_0009].
  - *Verified Output:* `8468000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json
- **[Line 17] [LEDGER_0009]**: Balance sheet cash and marketable securities totaled $10,605M [LEDGER_0007] against total debt of $8,468M [LEDGER_0008], resulting in a net debt of -$2,137M [LEDGER_0009].
  - *Verified Output:* `-2137000000.0` via `tools.calc.net_debt`
  - *Source:* Calculated: Total Debt - Liquid Assets
- **[Line 18] [LEDGER_0010]**: Current market price trades at $239.24 USD [LEDGER_0010].
  - *Verified Output:* `239.24` via `yfinance.quote`
  - *Source:* Yahoo Finance Market Quote
- **[Line 19] [LEDGER_0021]**: Baseline DCF fair value estimate is $82.66 [LEDGER_0021].
  - *Verified Output:* `82.65674569026157` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 20] [LEDGER_0022]**: Reverse DCF model indicates the current market price implies a 5-year FCF CAGR of 34.38% [LEDGER_0022].
  - *Verified Output:* `34.38429236412048` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 28] [LEDGER_0001]**: | Total Net Sales | $215,938M | [LEDGER_0001] | Primary Audited Filing |
  - *Verified Output:* `215938000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json (Accn: 0001045810-26-000021)
- **[Line 29] [LEDGER_0003]**: | Operating Income | $130,387M | [LEDGER_0003] | Primary Audited Filing |
  - *Verified Output:* `130387000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json (Accn: 0001045810-26-000021)
- **[Line 30] [LEDGER_0004]**: | Net Income | $120,067M | [LEDGER_0004] | Primary Audited Filing |
  - *Verified Output:* `120067000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json (Accn: 0001045810-26-000021)
- **[Line 31] [LEDGER_0005]**: | Operating Cash Flow | $102,718M | [LEDGER_0005] | Primary Audited Filing |
  - *Verified Output:* `102718000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json (Accn: 0001045810-26-000021)
- **[Line 32] [LEDGER_0006]**: | Capital Expenditures | $6,042M | [LEDGER_0006] | Primary Audited Filing |
  - *Verified Output:* `6042000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json
- **[Line 33] [LEDGER_0019]**: | Free Cash Flow | $96,676M | [LEDGER_0019] | Calculated: OCF - Capex |
  - *Verified Output:* `96676000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 34] [LEDGER_0007]**: | Total Cash & Marketable Securities | $10,605M | [LEDGER_0007] | Audited Balance Sheet |
  - *Verified Output:* `10605000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json
- **[Line 35] [LEDGER_0008]**: | Total Debt Obligations | $8,468M | [LEDGER_0008] | Audited Balance Sheet |
  - *Verified Output:* `8468000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json
- **[Line 36] [LEDGER_0009]**: | Net Debt Position | -$2,137M | [LEDGER_0009] | Calculated: Total Debt - Liquid Assets |
  - *Verified Output:* `-2137000000.0` via `tools.calc.net_debt`
  - *Source:* Calculated: Total Debt - Liquid Assets
- **[Line 44] [LEDGER_0022]**: [ANALYSIS] The implied growth rate of 34.38% [LEDGER_0022] exceeds the baseline growth assumption and reflects a premium multiple.
  - *Verified Output:* `34.38429236412048` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 42] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] NVIDIA CORP maintains competitive market positioning across its core operating business lines.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 43] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Multi-year customer relationships and global distribution support continuous operations.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*