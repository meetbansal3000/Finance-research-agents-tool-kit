# Verification Audit Report
**Target Report:** `tcs_research_report.md`  
**Audit Timestamp:** 2026-10-06T01:02:55.187151  
**Overall Status:** **PASS WITH FLAGS** (19 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (19)
- **[Line 10] [LEDGER_0002]**: TCS reported FY2024 consolidated revenue of ₹240,893 Crore [LEDGER_0002], representing a YoY revenue growth of 6.85% [LEDGER_0008].
  - *Verified Output:* `2408930000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2024 Audited Financial Statements
- **[Line 10] [LEDGER_0008]**: TCS reported FY2024 consolidated revenue of ₹240,893 Crore [LEDGER_0002], representing a YoY revenue growth of 6.85% [LEDGER_0008].
  - *Verified Output:* `6.846064455463989` via `tools.calc.yoy_growth`
  - *Source:* tools.calc.metrics.yoy_growth
- **[Line 11] [LEDGER_0004]**: Operating profit (EBIT) was ₹59,200 Crore [LEDGER_0004], delivering an operating margin of 24.58% [LEDGER_0009].
  - *Verified Output:* `592000000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2024 Audited Financial Statements
- **[Line 11] [LEDGER_0009]**: Operating profit (EBIT) was ₹59,200 Crore [LEDGER_0004], delivering an operating margin of 24.58% [LEDGER_0009].
  - *Verified Output:* `24.575226345306838` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 12] [LEDGER_0005]**: Net profit reached ₹46,099 Crore [LEDGER_0005], delivering a net margin of 19.14% [LEDGER_0010].
  - *Verified Output:* `460990000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2024 Audited Financial Statements
- **[Line 12] [LEDGER_0010]**: Net profit reached ₹46,099 Crore [LEDGER_0005], delivering a net margin of 19.14% [LEDGER_0010].
  - *Verified Output:* `19.136712150207767` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 13] [LEDGER_0006]**: Cash generated from operations was ₹44,300 Crore [LEDGER_0006] and capital expenditures were ₹3,100 Crore [LEDGER_0007].
  - *Verified Output:* `443000000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2024 Cash Flow Statement
- **[Line 13] [LEDGER_0007]**: Cash generated from operations was ₹44,300 Crore [LEDGER_0006] and capital expenditures were ₹3,100 Crore [LEDGER_0007].
  - *Verified Output:* `31000000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2024 Cash Flow Statement
- **[Line 14] [LEDGER_0011]**: Free cash flow was ₹41,200 Crore [LEDGER_0011].
  - *Verified Output:* `412000000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 15] [LEDGER_0001]**: Current market price trades at ₹2114.40 INR [LEDGER_0001].
  - *Verified Output:* `2114.4` via `yfinance.quote`
  - *Source:* NSE / Yahoo Finance Live Market Quote
- **[Line 16] [LEDGER_0012]**: Baseline DCF fair value estimate is ₹1910.27 [LEDGER_0012].
  - *Verified Output:* `1910.2650218881963` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 17] [LEDGER_0013]**: Reverse DCF indicates the current market price implies a 5-year FCF CAGR of 9.35% [LEDGER_0013].
  - *Verified Output:* `9.352010488510132` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 25] [LEDGER_0002]**: | Total Revenue from Operations | ₹240,893 Crore | [LEDGER_0002] | TCS FY2024 Audited Annual Report |
  - *Verified Output:* `2408930000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2024 Audited Financial Statements
- **[Line 26] [LEDGER_0004]**: | Operating Profit (EBIT) | ₹59,200 Crore | [LEDGER_0004] | TCS FY2024 Audited Annual Report |
  - *Verified Output:* `592000000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2024 Audited Financial Statements
- **[Line 27] [LEDGER_0005]**: | Consolidated Net Profit | ₹46,099 Crore | [LEDGER_0005] | TCS FY2024 Audited Annual Report |
  - *Verified Output:* `460990000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2024 Audited Financial Statements
- **[Line 28] [LEDGER_0006]**: | Operating Cash Flow | ₹44,300 Crore | [LEDGER_0006] | TCS FY2024 Cash Flow Statement |
  - *Verified Output:* `443000000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2024 Cash Flow Statement
- **[Line 29] [LEDGER_0007]**: | Capital Expenditures | ₹3,100 Crore | [LEDGER_0007] | TCS FY2024 Cash Flow Statement |
  - *Verified Output:* `31000000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2024 Cash Flow Statement
- **[Line 30] [LEDGER_0011]**: | Free Cash Flow | ₹41,200 Crore | [LEDGER_0011] | Calculated: OCF - Capex |
  - *Verified Output:* `412000000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 38] [LEDGER_0013]**: [ANALYSIS] The implied growth rate of 9.35% [LEDGER_0013] reflects realistic multi-year digital transformation demand.
  - *Verified Output:* `9.352010488510132` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 36] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] TCS is one of the largest global IT services and consulting companies.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 37] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Client relationships in banking, financial services, and retail provide recurring contract visibility.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*