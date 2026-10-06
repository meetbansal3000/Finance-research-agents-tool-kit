# Verification Audit Report
**Target Report:** `tcs_skeptic_review.md`  
**Audit Timestamp:** 2026-10-06T15:43:41.560885  
**Overall Status:** **PASS WITH FLAGS** (45 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (45)
- **[Line 12] [LEDGER_0003]**: | Base Free Cash Flow | ₹449,710,000,000 | AUDITED DATA | [LEDGER_0003] | Audited Statement of Cash Flows |
  - *Verified Output:* `449710000000.0` via `filing.cash_flow`
  - *Source:* Audited Statement of Cash Flows
- **[Line 13] [LEDGER_0007]**: | Assumed 5Y FCF Growth Rate | 8.00% | ASSUMPTION | [LEDGER_0007] | Model Assumption (Unanchored Parameter) |
  - *Verified Output:* `8.0` via `thesis.assumption`
  - *Source:* Model Assumption (Unanchored Parameter)
- **[Line 15] [LEDGER_0009]**: | Terminal Growth Rate | 4.00% | ASSUMPTION | [LEDGER_0009] | Model Assumption (Unanchored Parameter) |
  - *Verified Output:* `4.0` via `thesis.assumption`
  - *Source:* Model Assumption (Unanchored Parameter)
- **[Line 16] [LEDGER_0002]**: | Shares Outstanding | 3,618,087,518 | MARKET DATA | [LEDGER_0002] | Share Registry & Market Data |
  - *Verified Output:* `3618087518.0` via `yfinance.quote`
  - *Source:* Share Registry / Market Data
- **[Line 17] [LEDGER_0004]**: | Liquid Cash & Securities | ₹417,330,000,000 | AUDITED DATA | [LEDGER_0004] | Audited Balance Sheet |
  - *Verified Output:* `417330000000.0` via `filing.balance_sheet`
  - *Source:* Audited Balance Sheet
- **[Line 18] [LEDGER_0005]**: | Total Debt | ₹112,830,000,000 | AUDITED DATA | [LEDGER_0005] | Audited Balance Sheet |
  - *Verified Output:* `112830000000.0` via `filing.balance_sheet`
  - *Source:* Audited Balance Sheet
- **[Line 19] [LEDGER_0006]**: | Balance Sheet Net Debt | ₹-304,500,000,000 | AUDITED DATA | [LEDGER_0006] | Audited Balance Sheet (Debt - Cash) |
  - *Verified Output:* `-304500000000.0` via `filing.balance_sheet`
  - *Source:* Audited Balance Sheet
- **[Line 27] [LEDGER_0018]**: | **6.0% Growth** [LEDGER_0018] | ₹2431.24 [LEDGER_0020] | ₹2093.10 [LEDGER_0021] | ₹1839.59 [LEDGER_0022] |
  - *Verified Output:* `6.0` via `thesis.assumption`
  - *Source:* Model Sensitivity Parameter (Downside)
- **[Line 27] [LEDGER_0020]**: | **6.0% Growth** [LEDGER_0018] | ₹2431.24 [LEDGER_0020] | ₹2093.10 [LEDGER_0021] | ₹1839.59 [LEDGER_0022] |
  - *Verified Output:* `2431.2364110274493` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 27] [LEDGER_0021]**: | **6.0% Growth** [LEDGER_0018] | ₹2431.24 [LEDGER_0020] | ₹2093.10 [LEDGER_0021] | ₹1839.59 [LEDGER_0022] |
  - *Verified Output:* `2093.1002123251437` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 27] [LEDGER_0022]**: | **6.0% Growth** [LEDGER_0018] | ₹2431.24 [LEDGER_0020] | ₹2093.10 [LEDGER_0021] | ₹1839.59 [LEDGER_0022] |
  - *Verified Output:* `1839.5850028444297` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 28] [LEDGER_0007]**: | **8.0% Growth (Base)** [LEDGER_0007] | ₹2638.13 [LEDGER_0023] | ₹2267.27 [LEDGER_0011] | ₹1989.32 [LEDGER_0025] |
  - *Verified Output:* `8.0` via `thesis.assumption`
  - *Source:* Model Assumption (Unanchored Parameter)
- **[Line 28] [LEDGER_0023]**: | **8.0% Growth (Base)** [LEDGER_0007] | ₹2638.13 [LEDGER_0023] | ₹2267.27 [LEDGER_0011] | ₹1989.32 [LEDGER_0025] |
  - *Verified Output:* `2638.1281368581786` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 28] [LEDGER_0011]**: | **8.0% Growth (Base)** [LEDGER_0007] | ₹2638.13 [LEDGER_0023] | ₹2267.27 [LEDGER_0011] | ₹1989.32 [LEDGER_0025] |
  - *Verified Output:* `2267.272417353121` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 28] [LEDGER_0025]**: | **8.0% Growth (Base)** [LEDGER_0007] | ₹2638.13 [LEDGER_0023] | ₹2267.27 [LEDGER_0011] | ₹1989.32 [LEDGER_0025] |
  - *Verified Output:* `1989.3152960480159` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 29] [LEDGER_0019]**: | **10.0% Growth** [LEDGER_0019] | ₹2860.08 [LEDGER_0026] | ₹2454.01 [LEDGER_0027] | ₹2149.75 [LEDGER_0028] |
  - *Verified Output:* `10.0` via `thesis.assumption`
  - *Source:* Model Sensitivity Parameter (Upside)
- **[Line 29] [LEDGER_0026]**: | **10.0% Growth** [LEDGER_0019] | ₹2860.08 [LEDGER_0026] | ₹2454.01 [LEDGER_0027] | ₹2149.75 [LEDGER_0028] |
  - *Verified Output:* `2860.0809908140354` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 29] [LEDGER_0027]**: | **10.0% Growth** [LEDGER_0019] | ₹2860.08 [LEDGER_0026] | ₹2454.01 [LEDGER_0027] | ₹2149.75 [LEDGER_0028] |
  - *Verified Output:* `2454.0089333189385` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 29] [LEDGER_0028]**: | **10.0% Growth** [LEDGER_0019] | ₹2860.08 [LEDGER_0026] | ₹2454.01 [LEDGER_0027] | ₹2149.75 [LEDGER_0028] |
  - *Verified Output:* `2149.7488363889493` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 35] [LEDGER_0001]**: Current Market Price: ₹2100.00 INR [LEDGER_0001]
  - *Verified Output:* `2100.0` via `yfinance.quote`
  - *Source:* Market Quote (TCS.NS)
- **[Line 36] [LEDGER_0010]**: Implied 5-Year FCF CAGR (Reverse DCF): **6.08%** [LEDGER_0010]
  - *Verified Output:* `6.081980466842651` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 37] [LEDGER_0011]**: Baseline Fair Value (DCF): **₹2267.27** [LEDGER_0011]
  - *Verified Output:* `2267.272417353121` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 38] [LEDGER_0012]**: Stressed Fair Value (-200 bps Margin): **₹2088.31** [LEDGER_0012]
  - *Verified Output:* `2088.3114197975683` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 39] [LEDGER_0013]**: Margin Stress Valuation Impact: **-7.89%** [LEDGER_0013]
  - *Verified Output:* `-7.893228717724045` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 40] [LEDGER_0014]**: Stressed Fair Value (+100 bps WACC): **₹1989.32** [LEDGER_0014]
  - *Verified Output:* `1989.3152960480159` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 41] [LEDGER_0015]**: WACC Stress Valuation Impact: **-12.26%** [LEDGER_0015]
  - *Verified Output:* `-12.259537900152303` via `tools.calc.wacc_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 42] [LEDGER_0016]**: Stressed Fair Value (Half-Growth): **₹1930.83** [LEDGER_0016]
  - *Verified Output:* `1930.8282841503428` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 43] [LEDGER_0017]**: Half-Growth Valuation Impact: **-14.84%** [LEDGER_0017]
  - *Verified Output:* `-14.839157863330458` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 51] [LEDGER_0010]**: | Valuation Feasibility | Implied CAGR 6.08% [LEDGER_0010] vs Hist +7.57% [LEDGER_0032] | [LEDGER_0010], [LEDGER_0032] | **PASS** |
  - *Verified Output:* `6.081980466842651` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 51] [LEDGER_0032]**: | Valuation Feasibility | Implied CAGR 6.08% [LEDGER_0010] vs Hist +7.57% [LEDGER_0032] | [LEDGER_0010], [LEDGER_0032] | **PASS** |
  - *Verified Output:* `7.568951734837448` via `tools.calc.cagr`
  - *Source:* tools.calc.metrics.cagr
- **[Line 51] [LEDGER_0010]**: | Valuation Feasibility | Implied CAGR 6.08% [LEDGER_0010] vs Hist +7.57% [LEDGER_0032] | [LEDGER_0010], [LEDGER_0032] | **PASS** |
  - *Verified Output:* `6.081980466842651` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 51] [LEDGER_0032]**: | Valuation Feasibility | Implied CAGR 6.08% [LEDGER_0010] vs Hist +7.57% [LEDGER_0032] | [LEDGER_0010], [LEDGER_0032] | **PASS** |
  - *Verified Output:* `7.568951734837448` via `tools.calc.cagr`
  - *Source:* tools.calc.metrics.cagr
- **[Line 52] [LEDGER_0013]**: | Margin Shock (-200 bps) | Impact -7.89% [LEDGER_0013] (₹2088.31 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `-7.893228717724045` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 52] [LEDGER_0012]**: | Margin Shock (-200 bps) | Impact -7.89% [LEDGER_0013] (₹2088.31 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `2088.3114197975683` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 52] [LEDGER_0013]**: | Margin Shock (-200 bps) | Impact -7.89% [LEDGER_0013] (₹2088.31 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `-7.893228717724045` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 52] [LEDGER_0012]**: | Margin Shock (-200 bps) | Impact -7.89% [LEDGER_0013] (₹2088.31 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `2088.3114197975683` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 54] [LEDGER_0016]**: | Half-Growth Stress | Stressed Fair Value ₹1930.83 [LEDGER_0016] (-14.84% [LEDGER_0017]) | [LEDGER_0016], [LEDGER_0017] | **PASS** |
  - *Verified Output:* `1930.8282841503428` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 54] [LEDGER_0017]**: | Half-Growth Stress | Stressed Fair Value ₹1930.83 [LEDGER_0016] (-14.84% [LEDGER_0017]) | [LEDGER_0016], [LEDGER_0017] | **PASS** |
  - *Verified Output:* `-14.839157863330458` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 54] [LEDGER_0016]**: | Half-Growth Stress | Stressed Fair Value ₹1930.83 [LEDGER_0016] (-14.84% [LEDGER_0017]) | [LEDGER_0016], [LEDGER_0017] | **PASS** |
  - *Verified Output:* `1930.8282841503428` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 54] [LEDGER_0017]**: | Half-Growth Stress | Stressed Fair Value ₹1930.83 [LEDGER_0016] (-14.84% [LEDGER_0017]) | [LEDGER_0016], [LEDGER_0017] | **PASS** |
  - *Verified Output:* `-14.839157863330458` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 55] [LEDGER_0039]**: | Receivables Divergence | Divergence -1.49% [LEDGER_0039] | [LEDGER_0039] | **PASS** |
  - *Verified Output:* `-1.4900524909223272` via `tools.calc.working_capital`
  - *Source:* tools.calc.working_capital
- **[Line 55] [LEDGER_0039]**: | Receivables Divergence | Divergence -1.49% [LEDGER_0039] | [LEDGER_0039] | **PASS** |
  - *Verified Output:* `-1.4900524909223272` via `tools.calc.working_capital`
  - *Source:* tools.calc.working_capital
- **[Line 57] [LEDGER_0040]**: | Refinancing / Debt Risk | ST Debt / Cash = 3.72% [LEDGER_0040] | [LEDGER_0040] | **PASS** |
  - *Verified Output:* `3.7236719143124146` via `tools.calc.liquidity`
  - *Source:* Annual Balance Sheet
- **[Line 57] [LEDGER_0040]**: | Refinancing / Debt Risk | ST Debt / Cash = 3.72% [LEDGER_0040] | [LEDGER_0040] | **PASS** |
  - *Verified Output:* `3.7236719143124146` via `tools.calc.liquidity`
  - *Source:* Annual Balance Sheet
- **[Line 64] [ANALYSIS]**: [ANALYSIS] VULNERABLE: All 6 quantitative checks passed, but qualitative empirical risks were identified.
  - *Verified Output:* `ANALYST_DEDUCTION` via `analyst.reasoning`
  - *Source:* Report Author Analysis

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 65] [MODEL_MEMORY_TAGGED]**: Unverified context: [UNVERIFIED: model memory] Discretionary tech spending in North America has experienced selective contract delays.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 66] [MODEL_MEMORY_TAGGED]**: Unverified context: [UNVERIFIED: model memory] Wage inflation and delivery costs create intermediate operating margin pressure.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*