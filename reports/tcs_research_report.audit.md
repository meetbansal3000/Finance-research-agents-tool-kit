# Verification Audit Report
**Target Report:** `tcs_research_report.md`  
**Audit Timestamp:** 2026-10-06T15:43:41.544560  
**Overall Status:** **PASS WITH FLAGS** (36 Confirmed, 0 Wrong, 1 Unverifiable)  

---

### ✅ 1. Confirmed Claims (36)
- **[Line 10] [LEDGER_0001]**: TCS reported FY2025 consolidated revenue of ₹255,324 Crore [LEDGER_0001], representing a YoY revenue growth of 5.99% [LEDGER_0018].
  - *Verified Output:* `2553240000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Consolidated Audited Statement of Profit and Loss))
- **[Line 10] [LEDGER_0018]**: TCS reported FY2025 consolidated revenue of ₹255,324 Crore [LEDGER_0001], representing a YoY revenue growth of 5.99% [LEDGER_0018].
  - *Verified Output:* `5.9906265437351855` via `tools.calc.yoy_growth`
  - *Source:* tools.calc.metrics.yoy_growth
- **[Line 11] [LEDGER_0003]**: Operating profit (EBIT) was ₹62,293 Crore [LEDGER_0003], delivering an operating margin of 24.40% [LEDGER_0019].
  - *Verified Output:* `622930000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss))
- **[Line 11] [LEDGER_0019]**: Operating profit (EBIT) was ₹62,293 Crore [LEDGER_0003], delivering an operating margin of 24.40% [LEDGER_0019].
  - *Verified Output:* `24.397628111732544` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 12] [LEDGER_0005]**: Attributable net profit reached ₹48,553 Crore [LEDGER_0005], delivering a net margin of 19.02% [LEDGER_0020].
  - *Verified Output:* `485530000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss, Attributable Share))
- **[Line 12] [LEDGER_0020]**: Attributable net profit reached ₹48,553 Crore [LEDGER_0005], delivering a net margin of 19.02% [LEDGER_0020].
  - *Verified Output:* `19.01623035828986` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 13] [LEDGER_0007]**: Cash generated from operations was ₹48,908 Crore [LEDGER_0007] and capital expenditures were ₹3,937 Crore [LEDGER_0008].
  - *Verified Output:* `489080000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Consolidated Statement of Cash Flows))
- **[Line 13] [LEDGER_0008]**: Cash generated from operations was ₹48,908 Crore [LEDGER_0007] and capital expenditures were ₹3,937 Crore [LEDGER_0008].
  - *Verified Output:* `39370000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Consolidated Statement of Cash Flows))
- **[Line 14] [LEDGER_0009]**: Statutory derived free cash flow was ₹44,971 Crore [LEDGER_0009].
  - *Verified Output:* `449710000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Calculated: OCF ₹48,908 Cr - Capex ₹3,937 Cr))
- **[Line 15] [LEDGER_0011]**: Balance sheet cash and current investments totaled ₹41,733 Crore [LEDGER_0011] against total debt of ₹11,283 Crore [LEDGER_0012], producing a net debt position of -₹30,450 Crore [LEDGER_0014].
  - *Verified Output:* `417330000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 15] [LEDGER_0012]**: Balance sheet cash and current investments totaled ₹41,733 Crore [LEDGER_0011] against total debt of ₹11,283 Crore [LEDGER_0012], producing a net debt position of -₹30,450 Crore [LEDGER_0014].
  - *Verified Output:* `112830000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 15] [LEDGER_0014]**: Balance sheet cash and current investments totaled ₹41,733 Crore [LEDGER_0011] against total debt of ₹11,283 Crore [LEDGER_0012], producing a net debt position of -₹30,450 Crore [LEDGER_0014].
  - *Verified Output:* `-304500000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 16] [LEDGER_0017]**: Current market price trades at ₹2100.00 INR [LEDGER_0017].
  - *Verified Output:* `2100.0` via `yfinance.quote`
  - *Source:* NSE / Yahoo Finance Live Market Quote
- **[Line 17] [LEDGER_0021]**: Baseline DCF fair value estimate is ₹2169.27 [LEDGER_0021].
  - *Verified Output:* `2169.2703950985974` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 18] [LEDGER_0022]**: Reverse DCF indicates the current market price implies a 5-year FCF CAGR of 6.08% [LEDGER_0022].
  - *Verified Output:* `6.081980466842651` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 26] [LEDGER_0001]**: | Total Revenue from Operations | ₹255,324 Crore | [LEDGER_0001] | TCS FY2025 Audited Results, Page 4 |
  - *Verified Output:* `2553240000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Consolidated Audited Statement of Profit and Loss))
- **[Line 27] [LEDGER_0003]**: | Operating Profit (EBIT) | ₹62,293 Crore | [LEDGER_0003] | TCS FY2025 Audited Results, Page 4 |
  - *Verified Output:* `622930000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss))
- **[Line 28] [LEDGER_0005]**: | Attributable Net Profit | ₹48,553 Crore | [LEDGER_0005] | TCS FY2025 Audited Results, Page 4 |
  - *Verified Output:* `485530000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss, Attributable Share))
- **[Line 29] [LEDGER_0007]**: | Operating Cash Flow | ₹48,908 Crore | [LEDGER_0007] | TCS FY2025 Statement of Cash Flows, Page 6 |
  - *Verified Output:* `489080000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Consolidated Statement of Cash Flows))
- **[Line 30] [LEDGER_0008]**: | Capital Expenditures | ₹3,937 Crore | [LEDGER_0008] | TCS FY2025 Statement of Cash Flows, Page 6 |
  - *Verified Output:* `39370000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Consolidated Statement of Cash Flows))
- **[Line 31] [LEDGER_0009]**: | Derived Free Cash Flow | ₹44,971 Crore | [LEDGER_0009] | Calculated: OCF - Capex |
  - *Verified Output:* `449710000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Calculated: OCF ₹48,908 Cr - Capex ₹3,937 Cr))
- **[Line 32] [LEDGER_0011]**: | Cash & Current Investments | ₹41,733 Crore | [LEDGER_0011] | TCS FY2025 Consolidated Balance Sheet, Page 5 |
  - *Verified Output:* `417330000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 33] [LEDGER_0012]**: | Total Borrowings & Lease Debt | ₹11,283 Crore | [LEDGER_0012] | TCS FY2025 Consolidated Balance Sheet, Page 5 |
  - *Verified Output:* `112830000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 34] [LEDGER_0014]**: | Net Debt Position | -₹30,450 Crore | [LEDGER_0014] | Calculated: Total Debt - Liquid Cash |
  - *Verified Output:* `-304500000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 5 (Consolidated Balance Sheet))
- **[Line 42] [LEDGER_0009]**: | Free Cash Flow (FCF) | ₹44,971 Crore [LEDGER_0009] | ₹46,449 Crore [LEDGER_0010] | [LEDGER_0009], [LEDGER_0010] | Statutory derived FCF equals operating cash flow minus capex. Company headline FCF excludes certain operating adjustments. |
  - *Verified Output:* `449710000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Calculated: OCF ₹48,908 Cr - Capex ₹3,937 Cr))
- **[Line 42] [LEDGER_0010]**: | Free Cash Flow (FCF) | ₹44,971 Crore [LEDGER_0009] | ₹46,449 Crore [LEDGER_0010] | [LEDGER_0009], [LEDGER_0010] | Statutory derived FCF equals operating cash flow minus capex. Company headline FCF excludes certain operating adjustments. |
  - *Verified Output:* `464490000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 1 (Financial Performance Highlights))
- **[Line 42] [LEDGER_0009]**: | Free Cash Flow (FCF) | ₹44,971 Crore [LEDGER_0009] | ₹46,449 Crore [LEDGER_0010] | [LEDGER_0009], [LEDGER_0010] | Statutory derived FCF equals operating cash flow minus capex. Company headline FCF excludes certain operating adjustments. |
  - *Verified Output:* `449710000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 6 (Calculated: OCF ₹48,908 Cr - Capex ₹3,937 Cr))
- **[Line 42] [LEDGER_0010]**: | Free Cash Flow (FCF) | ₹44,971 Crore [LEDGER_0009] | ₹46,449 Crore [LEDGER_0010] | [LEDGER_0009], [LEDGER_0010] | Statutory derived FCF equals operating cash flow minus capex. Company headline FCF excludes certain operating adjustments. |
  - *Verified Output:* `464490000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 1 (Financial Performance Highlights))
- **[Line 43] [LEDGER_0019]**: | Operating Profit Margin | 24.40% [LEDGER_0019] | 24.3% [LEDGER_0004] | [LEDGER_0019], [LEDGER_0004] | Derived EBIT margin is based on total operating profit divided by revenue. Headline margin reflects core EBIT before other income. |
  - *Verified Output:* `24.397628111732544` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 43] [LEDGER_0004]**: | Operating Profit Margin | 24.40% [LEDGER_0019] | 24.3% [LEDGER_0004] | [LEDGER_0019], [LEDGER_0004] | Derived EBIT margin is based on total operating profit divided by revenue. Headline margin reflects core EBIT before other income. |
  - *Verified Output:* `24.3` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 1 (FY25 Headline Highlights))
- **[Line 43] [LEDGER_0019]**: | Operating Profit Margin | 24.40% [LEDGER_0019] | 24.3% [LEDGER_0004] | [LEDGER_0019], [LEDGER_0004] | Derived EBIT margin is based on total operating profit divided by revenue. Headline margin reflects core EBIT before other income. |
  - *Verified Output:* `24.397628111732544` via `tools.calc.margin`
  - *Source:* tools.calc.metrics.margin
- **[Line 43] [LEDGER_0004]**: | Operating Profit Margin | 24.40% [LEDGER_0019] | 24.3% [LEDGER_0004] | [LEDGER_0019], [LEDGER_0004] | Derived EBIT margin is based on total operating profit divided by revenue. Headline margin reflects core EBIT before other income. |
  - *Verified Output:* `24.3` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 1 (FY25 Headline Highlights))
- **[Line 44] [LEDGER_0005]**: | Net Profit Basis | ₹48,553 Crore [LEDGER_0005] | ₹48,553 Crore [LEDGER_0005] | [LEDGER_0005] | Attributable net profit to equity shareholders is ₹48,553 Cr used consistently across all periods. |
  - *Verified Output:* `485530000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss, Attributable Share))
- **[Line 44] [LEDGER_0005]**: | Net Profit Basis | ₹48,553 Crore [LEDGER_0005] | ₹48,553 Crore [LEDGER_0005] | [LEDGER_0005] | Attributable net profit to equity shareholders is ₹48,553 Cr used consistently across all periods. |
  - *Verified Output:* `485530000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss, Attributable Share))
- **[Line 44] [LEDGER_0005]**: | Net Profit Basis | ₹48,553 Crore [LEDGER_0005] | ₹48,553 Crore [LEDGER_0005] | [LEDGER_0005] | Attributable net profit to equity shareholders is ₹48,553 Cr used consistently across all periods. |
  - *Verified Output:* `485530000000.0` via `tools.filing.extract_metric`
  - *Source:* https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q4/press-release.pdf (Page 4 (Statement of Profit and Loss, Attributable Share))
- **[Line 51] [LEDGER_0022]**: [ANALYSIS] The implied growth rate of 6.08% [LEDGER_0022] aligns with compound annual growth rate calculations.
  - *Verified Output:* `6.081980466842651` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (1)
- **[Line 50] [MODEL_MEMORY_TAGGED]**: [UNVERIFIED: model memory] TCS is a leading global IT services and consulting enterprise.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---

### ⚖️ 4. Derived vs Headline Reconciliations (2)
- **Free Cash Flow**: Derived `449710000000.0` [LEDGER_0009] vs Headline `464490000000.0` [LEDGER_0010] (Delta: -14780000000.00)
  - *Status:* RECONCILED
  - *Explanation:* Statutory FCF (₹44,971 Cr derived as OCF - Capex) differs from company headline FCF (₹46,449 Cr) due to working capital/operating exclusions.
- **Operating Margin**: Derived `24.397628111732544` [LEDGER_0019] vs Headline `24.3` [LEDGER_0004] (Delta: +0.10)
  - *Status:* RECONCILED
  - *Explanation:* Derived EBIT margin (24.40%) includes all operating other income line items, whereas headline operating margin (24.3%) reflects core segment EBIT.

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*