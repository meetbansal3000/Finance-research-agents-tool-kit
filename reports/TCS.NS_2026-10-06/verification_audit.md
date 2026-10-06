# Verification Audit Report
**Target Report:** `analyst_report.md`  
**Audit Timestamp:** 2026-10-06T16:11:41.547897  
**Overall Status:** **PASS WITH FLAGS** (26 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (26)
- **[Line 12] [LEDGER_0001]**: Tata Consultancy Services Limited reported FY2025 total revenue of ₹255,324 Crore [LEDGER_0001], reflecting YoY revenue growth of 5.99% [LEDGER_0018].
  - *Verified Output:* `2553240000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Consolidated Audited Statement of Profit and Loss))
- **[Line 12] [LEDGER_0018]**: Tata Consultancy Services Limited reported FY2025 total revenue of ₹255,324 Crore [LEDGER_0001], reflecting YoY revenue growth of 5.99% [LEDGER_0018].
  - *Verified Output:* `5.9906265437351855` via `tools.calc.yoy_growth`
  - *Source:* tools.calc.metrics.yoy_growth
- **[Line 13] [LEDGER_0003]**: Operating profit was ₹62,293 Crore [LEDGER_0003], yielding an operating margin of 24.40% [LEDGER_0019].
  - *Verified Output:* `622930000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss))
- **[Line 13] [LEDGER_0019]**: Operating profit was ₹62,293 Crore [LEDGER_0003], yielding an operating margin of 24.40% [LEDGER_0019].
  - *Verified Output:* `24.397628111732544` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 14] [LEDGER_0005]**: Attributable net profit reached ₹48,553 Crore [LEDGER_0005], delivering a net margin of 19.02% [LEDGER_0020].
  - *Verified Output:* `485530000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss, Attributable Share))
- **[Line 14] [LEDGER_0020]**: Attributable net profit reached ₹48,553 Crore [LEDGER_0005], delivering a net margin of 19.02% [LEDGER_0020].
  - *Verified Output:* `19.01623035828986` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 15] [LEDGER_0007]**: Cash flow from operations was ₹48,908 Crore [LEDGER_0007] against capital expenditures of ₹3,937 Crore [LEDGER_0008].
  - *Verified Output:* `489080000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Consolidated Statement of Cash Flows))
- **[Line 15] [LEDGER_0008]**: Cash flow from operations was ₹48,908 Crore [LEDGER_0007] against capital expenditures of ₹3,937 Crore [LEDGER_0008].
  - *Verified Output:* `39370000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Consolidated Statement of Cash Flows))
- **[Line 16] [LEDGER_0021]**: Free cash flow derived on a statutory basis was ₹44,971 Crore [LEDGER_0021], yielding an FCF yield of 5.92% [LEDGER_0022].
  - *Verified Output:* `449710000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 16] [LEDGER_0022]**: Free cash flow derived on a statutory basis was ₹44,971 Crore [LEDGER_0021], yielding an FCF yield of 5.92% [LEDGER_0022].
  - *Verified Output:* `5.918807048813324` via `tools.calc.fcf_yield`
  - *Source:* tools.calc.metrics.fcf_yield
- **[Line 17] [LEDGER_0011]**: Liquid cash and investment assets totaled ₹41,733 Crore [LEDGER_0011] against total debt obligations of ₹11,283 Crore [LEDGER_0012], maintaining a net debt position of -₹30,450 Crore [LEDGER_0014].
  - *Verified Output:* `417330000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 17] [LEDGER_0012]**: Liquid cash and investment assets totaled ₹41,733 Crore [LEDGER_0011] against total debt obligations of ₹11,283 Crore [LEDGER_0012], maintaining a net debt position of -₹30,450 Crore [LEDGER_0014].
  - *Verified Output:* `112830000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 17] [LEDGER_0014]**: Liquid cash and investment assets totaled ₹41,733 Crore [LEDGER_0011] against total debt obligations of ₹11,283 Crore [LEDGER_0012], maintaining a net debt position of -₹30,450 Crore [LEDGER_0014].
  - *Verified Output:* `-304500000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 18] [LEDGER_0017]**: Current market price trades at ₹2100.00 INR [LEDGER_0017].
  - *Verified Output:* `2100.0` via `yfinance.quote`
  - *Source:* Yahoo Finance / NSE Quote
- **[Line 19] [LEDGER_0023]**: Baseline DCF fair value estimate is ₹2290.05 [LEDGER_0023].
  - *Verified Output:* `2290.0497819259235` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 20] [LEDGER_0024]**: Reverse DCF model indicates current market valuation implies a 5-year FCF CAGR of 4.32% [LEDGER_0024].
  - *Verified Output:* `4.317206144332886` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 28] [LEDGER_0001]**: | Revenue from Operations | ₹255,324 Crore | [LEDGER_0001] | Audited Financial Results Release |
  - *Verified Output:* `2553240000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Consolidated Audited Statement of Profit and Loss))
- **[Line 29] [LEDGER_0003]**: | Operating Income | ₹62,293 Crore | [LEDGER_0003] | Audited Financial Results Release |
  - *Verified Output:* `622930000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss))
- **[Line 30] [LEDGER_0005]**: | Attributable Net Profit | ₹48,553 Crore | [LEDGER_0005] | Audited Consolidated Statement |
  - *Verified Output:* `485530000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss, Attributable Share))
- **[Line 31] [LEDGER_0007]**: | Operating Cash Flow | ₹48,908 Crore | [LEDGER_0007] | Audited Cash Flow Statement |
  - *Verified Output:* `489080000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Consolidated Statement of Cash Flows))
- **[Line 32] [LEDGER_0008]**: | Capital Expenditures | ₹3,937 Crore | [LEDGER_0008] | Audited Cash Flow Statement |
  - *Verified Output:* `39370000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Consolidated Statement of Cash Flows))
- **[Line 33] [LEDGER_0021]**: | Derived Free Cash Flow | ₹44,971 Crore | [LEDGER_0021] | Calculated: OCF - Capex |
  - *Verified Output:* `449710000000.0` via `tools.calc.free_cash_flow`
  - *Source:* tools.calc.metrics.free_cash_flow
- **[Line 34] [LEDGER_0011]**: | Cash and Current Investments | ₹41,733 Crore | [LEDGER_0011] | Audited Balance Sheet |
  - *Verified Output:* `417330000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 35] [LEDGER_0012]**: | Total Debt Obligations | ₹11,283 Crore | [LEDGER_0012] | Audited Balance Sheet |
  - *Verified Output:* `112830000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 36] [LEDGER_0014]**: | Net Debt Buffer | -₹30,450 Crore | [LEDGER_0014] | Calculated: Total Debt - Liquid Cash |
  - *Verified Output:* `-304500000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 44] [LEDGER_0024]**: [ANALYSIS] The implied growth rate of 4.32% [LEDGER_0024] reflects market valuation expectations relative to historical compounding.
  - *Verified Output:* `4.317206144332886` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 42] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] The company commands global leadership across enterprise IT services, cloud migration, and cognitive business operations.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 43] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] Strong long-term multi-year customer relationships underpin industry-leading return metrics.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---

### ⚖️ 4. Derived vs Headline Reconciliations (2)
- **Free Cash Flow**: Derived `449710000000.0` [LEDGER_0021] vs Headline `464490000000.0` [LEDGER_0010] (Delta: -14780000000.00)
  - *Status:* RECONCILED
  - *Explanation:* Statutory FCF (₹44,971 Cr derived as OCF - Capex) differs from company headline FCF (₹46,449 Cr) due to working capital/operating exclusions.
- **Operating Margin**: Derived `24.397628111732544` [LEDGER_0019] vs Headline `24.3` [LEDGER_0004] (Delta: +0.10)
  - *Status:* RECONCILED
  - *Explanation:* Derived EBIT margin (24.40%) includes all operating other income line items, whereas headline operating margin (24.3%) reflects core segment EBIT.

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*