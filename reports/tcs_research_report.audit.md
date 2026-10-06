# Verification Audit Report
**Target Report:** `tcs_research_report.md`  
**Audit Timestamp:** 2026-10-06T15:09:30.370006  
**Overall Status:** **PASS WITH FLAGS** (19 Confirmed, 0 Wrong, 1 Unverifiable)  

---

### ✅ 1. Confirmed Claims (19)
- **[Line 10] [LEDGER_0002]**: TCS reported FY2025 consolidated revenue of ₹255,324 Crore [LEDGER_0002], representing a YoY revenue growth of 5.99% [LEDGER_0008].
  - *Verified Output:* `2553240000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2025 Audited Financial Statements, Page 168
- **[Line 10] [LEDGER_0008]**: TCS reported FY2025 consolidated revenue of ₹255,324 Crore [LEDGER_0002], representing a YoY revenue growth of 5.99% [LEDGER_0008].
  - *Verified Output:* `5.9906265437351855` via `tools.calc.yoy_growth`
  - *Source:* tools.calc.metrics.yoy_growth
- **[Line 11] [LEDGER_0004]**: Operating profit (EBIT) was ₹62,293 Crore [LEDGER_0004], delivering an operating margin of 24.40% [LEDGER_0009].
  - *Verified Output:* `622930000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2025 Audited Financial Statements, Page 168
- **[Line 11] [LEDGER_0009]**: Operating profit (EBIT) was ₹62,293 Crore [LEDGER_0004], delivering an operating margin of 24.40% [LEDGER_0009].
  - *Verified Output:* `24.397628111732544` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 12] [LEDGER_0005]**: Net profit reached ₹48,553 Crore [LEDGER_0005], delivering a net margin of 19.02% [LEDGER_0010].
  - *Verified Output:* `485530000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2025 Audited Financial Statements, Page 168
- **[Line 12] [LEDGER_0010]**: Net profit reached ₹48,553 Crore [LEDGER_0005], delivering a net margin of 19.02% [LEDGER_0010].
  - *Verified Output:* `19.01623035828986` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 13] [LEDGER_0006]**: Cash generated from operations was ₹48,908 Crore [LEDGER_0006] and capital expenditures were ₹3,937 Crore [LEDGER_0007].
  - *Verified Output:* `489080000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2025 Consolidated Statement of Cash Flows, Page 174
- **[Line 13] [LEDGER_0007]**: Cash generated from operations was ₹48,908 Crore [LEDGER_0006] and capital expenditures were ₹3,937 Crore [LEDGER_0007].
  - *Verified Output:* `39370000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2025 Consolidated Statement of Cash Flows, Page 174
- **[Line 14] [LEDGER_0011]**: Free cash flow was ₹44,971 Crore [LEDGER_0011].
  - *Verified Output:* `449710000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 15] [LEDGER_0001]**: Current market price trades at ₹2100.00 INR [LEDGER_0001].
  - *Verified Output:* `2100.0` via `yfinance.quote`
  - *Source:* NSE / Yahoo Finance Live Market Quote
- **[Line 16] [LEDGER_0012]**: Baseline DCF fair value estimate is ₹2085.11 [LEDGER_0012].
  - *Verified Output:* `2085.109910178011` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 17] [LEDGER_0013]**: Reverse DCF indicates the current market price implies a 5-year FCF CAGR of 7.06% [LEDGER_0013].
  - *Verified Output:* `7.0631325244903564` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 25] [LEDGER_0002]**: | Total Revenue from Operations | ₹255,324 Crore | [LEDGER_0002] | TCS FY2025 Audited Annual Report, Page 168 |
  - *Verified Output:* `2553240000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2025 Audited Financial Statements, Page 168
- **[Line 26] [LEDGER_0004]**: | Operating Profit (EBIT) | ₹62,293 Crore | [LEDGER_0004] | TCS FY2025 Audited Annual Report, Page 168 |
  - *Verified Output:* `622930000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2025 Audited Financial Statements, Page 168
- **[Line 27] [LEDGER_0005]**: | Consolidated Net Profit | ₹48,553 Crore | [LEDGER_0005] | TCS FY2025 Audited Annual Report, Page 168 |
  - *Verified Output:* `485530000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2025 Audited Financial Statements, Page 168
- **[Line 28] [LEDGER_0006]**: | Operating Cash Flow | ₹48,908 Crore | [LEDGER_0006] | TCS FY2025 Cash Flow Statement, Page 174 |
  - *Verified Output:* `489080000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2025 Consolidated Statement of Cash Flows, Page 174
- **[Line 29] [LEDGER_0007]**: | Capital Expenditures | ₹3,937 Crore | [LEDGER_0007] | TCS FY2025 Cash Flow Statement, Page 174 |
  - *Verified Output:* `39370000000.0` via `filing.financials`
  - *Source:* TCS Annual Report FY2025 Consolidated Statement of Cash Flows, Page 174
- **[Line 30] [LEDGER_0011]**: | Free Cash Flow | ₹44,971 Crore | [LEDGER_0011] | Calculated: OCF - Capex |
  - *Verified Output:* `449710000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 37] [LEDGER_0013]**: [ANALYSIS] The implied growth rate of 7.06% [LEDGER_0013] aligns with compound annual growth rate calculations.
  - *Verified Output:* `7.0631325244903564` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (1)
- **[Line 36] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] TCS is a leading global IT services and consulting enterprise.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*