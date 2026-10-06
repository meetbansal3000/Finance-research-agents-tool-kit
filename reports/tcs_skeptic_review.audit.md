# Verification Audit Report
**Target Report:** `tcs_skeptic_review.md`  
**Audit Timestamp:** 2026-10-06T15:09:30.383399  
**Overall Status:** **PASS WITH FLAGS** (36 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (36)
- **[Line 12] [LEDGER_0002]**: | Base Free Cash Flow | ₹449,710,000,000 | [LEDGER_0002] | Audited Statement of Cash Flows |
  - *Verified Output:* `449710000000.0` via `filing.cash_flow`
  - *Source:* Audited Cash Flow Statement
- **[Line 13] [LEDGER_0003]**: | Assumed 5Y FCF Growth Rate | 8.00% | [LEDGER_0003] | Analyst Thesis Model |
  - *Verified Output:* `8.0` via `thesis.assumption`
  - *Source:* Analyst Thesis Model Assumption
- **[Line 14] [LEDGER_0004]**: | Discount Rate (WACC) | 11.00% | [LEDGER_0004] | Cost of Capital Model |
  - *Verified Output:* `11.0` via `thesis.assumption`
  - *Source:* Cost of Capital Assumption
- **[Line 15] [LEDGER_0005]**: | Terminal Growth Rate | 4.00% | [LEDGER_0005] | Long-term GDP Baseline |
  - *Verified Output:* `4.0` via `thesis.assumption`
  - *Source:* Terminal Growth Assumption
- **[Line 16] [LEDGER_0006]**: | Shares Outstanding | 3,618,087,518 | [LEDGER_0006] | Market & Share Registry Data |
  - *Verified Output:* `3618087518.0` via `yfinance.quote`
  - *Source:* Share Registry / Market Data
- **[Line 17] [LEDGER_0007]**: | Net Debt | ₹0 | [LEDGER_0007] | Audited Balance Sheet |
  - *Verified Output:* `0.0` via `filing.balance_sheet`
  - *Source:* Audited Balance Sheet
- **[Line 23] [LEDGER_0001]**: Current Market Price: ₹2100.00 INR [LEDGER_0001]
  - *Verified Output:* `2100.0` via `yfinance.quote`
  - *Source:* Market Quote (TCS.NS)
- **[Line 24] [LEDGER_0008]**: Implied 5-Year FCF CAGR (Reverse DCF): **7.06%** [LEDGER_0008]
  - *Verified Output:* `7.0631325244903564` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 25] [LEDGER_0009]**: Baseline Fair Value (DCF): **₹2183.11** [LEDGER_0009]
  - *Verified Output:* `2183.111932432535` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 26] [LEDGER_0010]**: Stressed Fair Value (-200 bps Margin): **₹2004.15** [LEDGER_0010]
  - *Verified Output:* `2004.150934876982` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 27] [LEDGER_0011]**: Margin Stress Valuation Impact: **-8.20%** [LEDGER_0011]
  - *Verified Output:* `-8.19751818021284` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 28] [LEDGER_0012]**: Stressed Fair Value (+100 bps WACC): **₹1905.15** [LEDGER_0012]
  - *Verified Output:* `1905.1548111274296` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 29] [LEDGER_0013]**: WACC Stress Valuation Impact: **-12.73%** [LEDGER_0013]
  - *Verified Output:* `-12.73215162153373` via `tools.calc.wacc_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 30] [LEDGER_0014]**: Stressed Fair Value (Half-Growth): **₹1846.67** [LEDGER_0014]
  - *Verified Output:* `1846.6677992297568` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 31] [LEDGER_0015]**: Half-Growth Valuation Impact: **-15.41%** [LEDGER_0015]
  - *Verified Output:* `-15.411217730274366` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 39] [LEDGER_0008]**: | Valuation Feasibility | Implied CAGR 7.06% [LEDGER_0008] vs Hist +7.57% [LEDGER_0019] | [LEDGER_0008], [LEDGER_0019] | **PASS** |
  - *Verified Output:* `7.0631325244903564` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 39] [LEDGER_0019]**: | Valuation Feasibility | Implied CAGR 7.06% [LEDGER_0008] vs Hist +7.57% [LEDGER_0019] | [LEDGER_0008], [LEDGER_0019] | **PASS** |
  - *Verified Output:* `7.568951734837448` via `tools.calc.cagr`
  - *Source:* tools.calc.metrics.cagr
- **[Line 39] [LEDGER_0008]**: | Valuation Feasibility | Implied CAGR 7.06% [LEDGER_0008] vs Hist +7.57% [LEDGER_0019] | [LEDGER_0008], [LEDGER_0019] | **PASS** |
  - *Verified Output:* `7.0631325244903564` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 39] [LEDGER_0019]**: | Valuation Feasibility | Implied CAGR 7.06% [LEDGER_0008] vs Hist +7.57% [LEDGER_0019] | [LEDGER_0008], [LEDGER_0019] | **PASS** |
  - *Verified Output:* `7.568951734837448` via `tools.calc.cagr`
  - *Source:* tools.calc.metrics.cagr
- **[Line 40] [LEDGER_0011]**: | Margin Shock (-200 bps) | Impact -8.20% [LEDGER_0011] (₹2004.15 [LEDGER_0010]) | [LEDGER_0011], [LEDGER_0010] | **PASS** |
  - *Verified Output:* `-8.19751818021284` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 40] [LEDGER_0010]**: | Margin Shock (-200 bps) | Impact -8.20% [LEDGER_0011] (₹2004.15 [LEDGER_0010]) | [LEDGER_0011], [LEDGER_0010] | **PASS** |
  - *Verified Output:* `2004.150934876982` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 40] [LEDGER_0011]**: | Margin Shock (-200 bps) | Impact -8.20% [LEDGER_0011] (₹2004.15 [LEDGER_0010]) | [LEDGER_0011], [LEDGER_0010] | **PASS** |
  - *Verified Output:* `-8.19751818021284` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 40] [LEDGER_0010]**: | Margin Shock (-200 bps) | Impact -8.20% [LEDGER_0011] (₹2004.15 [LEDGER_0010]) | [LEDGER_0011], [LEDGER_0010] | **PASS** |
  - *Verified Output:* `2004.150934876982` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 41] [LEDGER_0013]**: | WACC Shock (+100 bps) | Impact -12.73% [LEDGER_0013] (₹1905.15 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `-12.73215162153373` via `tools.calc.wacc_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 41] [LEDGER_0012]**: | WACC Shock (+100 bps) | Impact -12.73% [LEDGER_0013] (₹1905.15 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `1905.1548111274296` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 41] [LEDGER_0013]**: | WACC Shock (+100 bps) | Impact -12.73% [LEDGER_0013] (₹1905.15 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `-12.73215162153373` via `tools.calc.wacc_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 41] [LEDGER_0012]**: | WACC Shock (+100 bps) | Impact -12.73% [LEDGER_0013] (₹1905.15 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `1905.1548111274296` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 42] [LEDGER_0014]**: | Half-Growth Stress | Stressed Fair Value ₹1846.67 [LEDGER_0014] (-15.41% [LEDGER_0015]) | [LEDGER_0014], [LEDGER_0015] | **PASS** |
  - *Verified Output:* `1846.6677992297568` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 42] [LEDGER_0015]**: | Half-Growth Stress | Stressed Fair Value ₹1846.67 [LEDGER_0014] (-15.41% [LEDGER_0015]) | [LEDGER_0014], [LEDGER_0015] | **PASS** |
  - *Verified Output:* `-15.411217730274366` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 42] [LEDGER_0014]**: | Half-Growth Stress | Stressed Fair Value ₹1846.67 [LEDGER_0014] (-15.41% [LEDGER_0015]) | [LEDGER_0014], [LEDGER_0015] | **PASS** |
  - *Verified Output:* `1846.6677992297568` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 42] [LEDGER_0015]**: | Half-Growth Stress | Stressed Fair Value ₹1846.67 [LEDGER_0014] (-15.41% [LEDGER_0015]) | [LEDGER_0014], [LEDGER_0015] | **PASS** |
  - *Verified Output:* `-15.411217730274366` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 43] [LEDGER_0020]**: | Receivables Divergence | Divergence -1.49% [LEDGER_0020] | [LEDGER_0020] | **PASS** |
  - *Verified Output:* `-1.4906265437351858` via `tools.calc.working_capital`
  - *Source:* Annual Filings
- **[Line 43] [LEDGER_0020]**: | Receivables Divergence | Divergence -1.49% [LEDGER_0020] | [LEDGER_0020] | **PASS** |
  - *Verified Output:* `-1.4906265437351858` via `tools.calc.working_capital`
  - *Source:* Annual Filings
- **[Line 45] [LEDGER_0021]**: | Refinancing / Debt Risk | ST Debt / Cash = 3.72% [LEDGER_0021] | [LEDGER_0021] | **PASS** |
  - *Verified Output:* `3.7236719143124146` via `tools.calc.liquidity`
  - *Source:* Annual Balance Sheet
- **[Line 45] [LEDGER_0021]**: | Refinancing / Debt Risk | ST Debt / Cash = 3.72% [LEDGER_0021] | [LEDGER_0021] | **PASS** |
  - *Verified Output:* `3.7236719143124146` via `tools.calc.liquidity`
  - *Source:* Annual Balance Sheet
- **[Line 52] [ANALYSIS]**: [ANALYSIS] VULNERABLE: All 6 quantitative checks passed, but qualitative empirical risks were identified.
  - *Verified Output:* `ANALYST_DEDUCTION` via `analyst.reasoning`
  - *Source:* Report Author Analysis

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 53] [MODEL_MEMORY_TAGGED]**: Unverified context: [UNVERIFIED: model memory] Discretionary tech spending in North America has experienced selective contract delays.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 54] [MODEL_MEMORY_TAGGED]**: Unverified context: [UNVERIFIED: model memory] Wage inflation and delivery costs create intermediate operating margin pressure.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*