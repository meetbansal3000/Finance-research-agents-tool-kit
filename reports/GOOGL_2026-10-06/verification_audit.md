# Verification Audit Report
**Target Report:** `analyst_report.md`  
**Audit Timestamp:** 2026-10-06T22:36:25.923617  
**Overall Status:** **PASS WITH FLAGS (NOT RE-FETCHED)** (26 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (26)
- **[Line 12] [LEDGER_0001]**: Alphabet Inc. reported FY2025 total revenue of $402,836M [LEDGER_0001], representing a YoY revenue growth of 15.09% [LEDGER_0014].
  - *Verified Output:* `402836000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json (Accn: 0001652044-26-000018)
- **[Line 12] [LEDGER_0014]**: Alphabet Inc. reported FY2025 total revenue of $402,836M [LEDGER_0001], representing a YoY revenue growth of 15.09% [LEDGER_0014].
  - *Verified Output:* `15.090081081544376` via `tools.calc.yoy_growth`
  - *Source:* tools.calc.metrics.yoy_growth
- **[Line 13] [LEDGER_0003]**: Operating income was $129,039M [LEDGER_0003], resulting in an operating margin of 32.03% [LEDGER_0015].
  - *Verified Output:* `129039000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json (Accn: 0001652044-26-000018)
- **[Line 13] [LEDGER_0015]**: Operating income was $129,039M [LEDGER_0003], resulting in an operating margin of 32.03% [LEDGER_0015].
  - *Verified Output:* `32.032638592380025` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 14] [LEDGER_0004]**: Net income reached $132,170M [LEDGER_0004], delivering a net margin of 32.81% [LEDGER_0016].
  - *Verified Output:* `132170000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json (Accn: 0001652044-26-000018)
- **[Line 14] [LEDGER_0016]**: Net income reached $132,170M [LEDGER_0004], delivering a net margin of 32.81% [LEDGER_0016].
  - *Verified Output:* `32.80987796522654` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 15] [LEDGER_0005]**: Cash flow from operations was $164,713M [LEDGER_0005] and capital expenditures were $91,447M [LEDGER_0006].
  - *Verified Output:* `164713000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json (Accn: 0001652044-26-000018)
- **[Line 15] [LEDGER_0006]**: Cash flow from operations was $164,713M [LEDGER_0005] and capital expenditures were $91,447M [LEDGER_0006].
  - *Verified Output:* `91447000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json
- **[Line 16] [LEDGER_0017]**: Free cash flow was $73,266M [LEDGER_0017], yielding an FCF yield of 3.59% [LEDGER_0018].
  - *Verified Output:* `73266000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 16] [LEDGER_0018]**: Free cash flow was $73,266M [LEDGER_0017], yielding an FCF yield of 3.59% [LEDGER_0018].
  - *Verified Output:* `3.5916594583465855` via `tools.calc.fcf_yield`
  - *Source:* tools.calc.metrics.fcf_yield
- **[Line 17] [LEDGER_0007]**: Balance sheet cash and marketable securities totaled $126,843M [LEDGER_0007] against total debt of $48,543M [LEDGER_0008], resulting in a net debt of -$78,300M [LEDGER_0009].
  - *Verified Output:* `126843000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json
- **[Line 17] [LEDGER_0008]**: Balance sheet cash and marketable securities totaled $126,843M [LEDGER_0007] against total debt of $48,543M [LEDGER_0008], resulting in a net debt of -$78,300M [LEDGER_0009].
  - *Verified Output:* `48543000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json
- **[Line 17] [LEDGER_0009]**: Balance sheet cash and marketable securities totaled $126,843M [LEDGER_0007] against total debt of $48,543M [LEDGER_0008], resulting in a net debt of -$78,300M [LEDGER_0009].
  - *Verified Output:* `-78300000000.0` via `tools.calc.net_debt`
  - *Source:* Calculated: Total Debt - Liquid Assets
- **[Line 18] [LEDGER_0010]**: Current market price trades at $347.68 USD [LEDGER_0010].
  - *Verified Output:* `347.68` via `yfinance.quote`
  - *Source:* Yahoo Finance Market Quote
- **[Line 19] [LEDGER_0019]**: Baseline DCF fair value estimate is $283.38 [LEDGER_0019].
  - *Verified Output:* `283.3825000087262` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 20] [LEDGER_0020]**: Reverse DCF model indicates the current market price implies a 5-year FCF CAGR of 13.17% [LEDGER_0020].
  - *Verified Output:* `13.169509172439575` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 28] [LEDGER_0001]**: | Total Net Sales | $402,836M | [LEDGER_0001] | Primary Audited Filing |
  - *Verified Output:* `402836000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json (Accn: 0001652044-26-000018)
- **[Line 29] [LEDGER_0003]**: | Operating Income | $129,039M | [LEDGER_0003] | Primary Audited Filing |
  - *Verified Output:* `129039000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json (Accn: 0001652044-26-000018)
- **[Line 30] [LEDGER_0004]**: | Net Income | $132,170M | [LEDGER_0004] | Primary Audited Filing |
  - *Verified Output:* `132170000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json (Accn: 0001652044-26-000018)
- **[Line 31] [LEDGER_0005]**: | Operating Cash Flow | $164,713M | [LEDGER_0005] | Primary Audited Filing |
  - *Verified Output:* `164713000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json (Accn: 0001652044-26-000018)
- **[Line 32] [LEDGER_0006]**: | Capital Expenditures | $91,447M | [LEDGER_0006] | Primary Audited Filing |
  - *Verified Output:* `91447000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json
- **[Line 33] [LEDGER_0017]**: | Free Cash Flow | $73,266M | [LEDGER_0017] | Calculated: OCF - Capex |
  - *Verified Output:* `73266000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 34] [LEDGER_0007]**: | Total Cash & Marketable Securities | $126,843M | [LEDGER_0007] | Audited Balance Sheet |
  - *Verified Output:* `126843000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json
- **[Line 35] [LEDGER_0008]**: | Total Debt Obligations | $48,543M | [LEDGER_0008] | Audited Balance Sheet |
  - *Verified Output:* `48543000000.0` via `edgar.get_facts`
  - *Source:* https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json
- **[Line 36] [LEDGER_0009]**: | Net Debt Position | -$78,300M | [LEDGER_0009] | Calculated: Total Debt - Liquid Assets |
  - *Verified Output:* `-78300000000.0` via `tools.calc.net_debt`
  - *Source:* Calculated: Total Debt - Liquid Assets
- **[Line 44] [LEDGER_0020]**: [ANALYSIS] The implied growth rate of 13.17% [LEDGER_0020] exceeds the baseline growth assumption and reflects a premium multiple.
  - *Verified Output:* `13.169509172439575` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 42] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Alphabet Inc. maintains competitive market positioning across its core operating business lines.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 43] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Multi-year customer relationships and global distribution support continuous operations.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*