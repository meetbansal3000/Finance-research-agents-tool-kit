# Verification Audit Report
**Target Report:** `aapl_skeptic_review.md`  
**Audit Timestamp:** 2026-10-06T01:02:55.039849  
**Overall Status:** **PASS WITH FLAGS** (36 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (36)
- **[Line 10] [LEDGER_0001]**: Current Market Price: $332.89 USD [LEDGER_0001]
  - *Verified Output:* `332.89` via `yfinance.quote`
  - *Source:* Market Quote (AAPL)
- **[Line 11] [LEDGER_0002]**: Implied 5-Year FCF CAGR (Reverse DCF): **28.97%** [LEDGER_0002]
  - *Verified Output:* `28.970104455947876` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 12] [LEDGER_0003]**: Baseline Fair Value (DCF): **$146.35** [LEDGER_0003]
  - *Verified Output:* `146.3459176168883` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 13] [LEDGER_0004]**: Stressed Fair Value (-200 bps Margin): **$137.19** [LEDGER_0004]
  - *Verified Output:* `137.19094378428977` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 14] [LEDGER_0005]**: Margin Stress Valuation Impact: **-6.26%** [LEDGER_0005]
  - *Verified Output:* `-6.255708380308141` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 15] [LEDGER_0006]**: Stressed Fair Value (+100 bps WACC): **$124.96** [LEDGER_0006]
  - *Verified Output:* `124.96477467593226` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 16] [LEDGER_0007]**: WACC Stress Valuation Impact: **-14.61%** [LEDGER_0007]
  - *Verified Output:* `-14.61000299094688` via `tools.calc.wacc_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 17] [LEDGER_0008]**: Stressed Fair Value (Half-Growth): **$123.40** [LEDGER_0008]
  - *Verified Output:* `123.39874627773258` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 18] [LEDGER_0009]**: Half-Growth Valuation Impact: **-15.68%** [LEDGER_0009]
  - *Verified Output:* `-15.680089826098174` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 26] [LEDGER_0002]**: | Valuation Feasibility | Implied CAGR 28.97% [LEDGER_0002] vs Hist 4.00% [LEDGER_0010] | [LEDGER_0002], [LEDGER_0010] | **FAIL** |
  - *Verified Output:* `28.970104455947876` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 26] [LEDGER_0010]**: | Valuation Feasibility | Implied CAGR 28.97% [LEDGER_0002] vs Hist 4.00% [LEDGER_0010] | [LEDGER_0002], [LEDGER_0010] | **FAIL** |
  - *Verified Output:* `4.0` via `tools.calc.cagr`
  - *Source:* SEC 10-K / Annual Filings
- **[Line 26] [LEDGER_0002]**: | Valuation Feasibility | Implied CAGR 28.97% [LEDGER_0002] vs Hist 4.00% [LEDGER_0010] | [LEDGER_0002], [LEDGER_0010] | **FAIL** |
  - *Verified Output:* `28.970104455947876` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 26] [LEDGER_0010]**: | Valuation Feasibility | Implied CAGR 28.97% [LEDGER_0002] vs Hist 4.00% [LEDGER_0010] | [LEDGER_0002], [LEDGER_0010] | **FAIL** |
  - *Verified Output:* `4.0` via `tools.calc.cagr`
  - *Source:* SEC 10-K / Annual Filings
- **[Line 27] [LEDGER_0005]**: | Margin Shock (-200 bps) | Impact -6.26% [LEDGER_0005] ($137.19 [LEDGER_0004]) | [LEDGER_0005], [LEDGER_0004] | **PASS** |
  - *Verified Output:* `-6.255708380308141` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 27] [LEDGER_0004]**: | Margin Shock (-200 bps) | Impact -6.26% [LEDGER_0005] ($137.19 [LEDGER_0004]) | [LEDGER_0005], [LEDGER_0004] | **PASS** |
  - *Verified Output:* `137.19094378428977` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 27] [LEDGER_0005]**: | Margin Shock (-200 bps) | Impact -6.26% [LEDGER_0005] ($137.19 [LEDGER_0004]) | [LEDGER_0005], [LEDGER_0004] | **PASS** |
  - *Verified Output:* `-6.255708380308141` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 27] [LEDGER_0004]**: | Margin Shock (-200 bps) | Impact -6.26% [LEDGER_0005] ($137.19 [LEDGER_0004]) | [LEDGER_0005], [LEDGER_0004] | **PASS** |
  - *Verified Output:* `137.19094378428977` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 28] [LEDGER_0007]**: | WACC Shock (+100 bps) | Impact -14.61% [LEDGER_0007] ($124.96 [LEDGER_0006]) | [LEDGER_0007], [LEDGER_0006] | **PASS** |
  - *Verified Output:* `-14.61000299094688` via `tools.calc.wacc_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 28] [LEDGER_0006]**: | WACC Shock (+100 bps) | Impact -14.61% [LEDGER_0007] ($124.96 [LEDGER_0006]) | [LEDGER_0007], [LEDGER_0006] | **PASS** |
  - *Verified Output:* `124.96477467593226` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 28] [LEDGER_0007]**: | WACC Shock (+100 bps) | Impact -14.61% [LEDGER_0007] ($124.96 [LEDGER_0006]) | [LEDGER_0007], [LEDGER_0006] | **PASS** |
  - *Verified Output:* `-14.61000299094688` via `tools.calc.wacc_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 28] [LEDGER_0006]**: | WACC Shock (+100 bps) | Impact -14.61% [LEDGER_0007] ($124.96 [LEDGER_0006]) | [LEDGER_0007], [LEDGER_0006] | **PASS** |
  - *Verified Output:* `124.96477467593226` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 29] [LEDGER_0008]**: | Half-Growth Stress | Stressed Fair Value $123.40 [LEDGER_0008] (-15.68% [LEDGER_0009]) | [LEDGER_0008], [LEDGER_0009] | **FAIL** |
  - *Verified Output:* `123.39874627773258` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 29] [LEDGER_0009]**: | Half-Growth Stress | Stressed Fair Value $123.40 [LEDGER_0008] (-15.68% [LEDGER_0009]) | [LEDGER_0008], [LEDGER_0009] | **FAIL** |
  - *Verified Output:* `-15.680089826098174` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 29] [LEDGER_0008]**: | Half-Growth Stress | Stressed Fair Value $123.40 [LEDGER_0008] (-15.68% [LEDGER_0009]) | [LEDGER_0008], [LEDGER_0009] | **FAIL** |
  - *Verified Output:* `123.39874627773258` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 29] [LEDGER_0009]**: | Half-Growth Stress | Stressed Fair Value $123.40 [LEDGER_0008] (-15.68% [LEDGER_0009]) | [LEDGER_0008], [LEDGER_0009] | **FAIL** |
  - *Verified Output:* `-15.680089826098174` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 30] [LEDGER_0011]**: | Receivables Divergence | Divergence -4.43% [LEDGER_0011] | [LEDGER_0011] | **PASS** |
  - *Verified Output:* `-4.425511782832739` via `tools.calc.working_capital`
  - *Source:* SEC 10-K / Annual Filings
- **[Line 30] [LEDGER_0011]**: | Receivables Divergence | Divergence -4.43% [LEDGER_0011] | [LEDGER_0011] | **PASS** |
  - *Verified Output:* `-4.425511782832739` via `tools.calc.working_capital`
  - *Source:* SEC 10-K / Annual Filings
- **[Line 31] [LEDGER_0012]**: | Inventory Divergence | Divergence -11.43% [LEDGER_0012] | [LEDGER_0012] | **FAIL** |
  - *Verified Output:* `-11.42551178283274` via `tools.calc.working_capital`
  - *Source:* SEC 10-K / Annual Filings
- **[Line 31] [LEDGER_0012]**: | Inventory Divergence | Divergence -11.43% [LEDGER_0012] | [LEDGER_0012] | **FAIL** |
  - *Verified Output:* `-11.42551178283274` via `tools.calc.working_capital`
  - *Source:* SEC 10-K / Annual Filings
- **[Line 32] [LEDGER_0013]**: | Refinancing / Debt Risk | ST Debt / Cash = 33.40% [LEDGER_0013] | [LEDGER_0013] | **PASS** |
  - *Verified Output:* `33.396787229068565` via `tools.calc.liquidity`
  - *Source:* SEC 10-K / Annual Filings
- **[Line 32] [LEDGER_0013]**: | Refinancing / Debt Risk | ST Debt / Cash = 33.40% [LEDGER_0013] | [LEDGER_0013] | **PASS** |
  - *Verified Output:* `33.396787229068565` via `tools.calc.liquidity`
  - *Source:* SEC 10-K / Annual Filings
- **[Line 39] [ANALYSIS]**: [ANALYSIS] VULNERABLE: Found 3 quantitative failure(s) across 7 performed checks.
  - *Verified Output:* `ANALYST_DEDUCTION` via `analyst.reasoning`
  - *Source:* Report Author Analysis
- **[Line 40] [LEDGER_0002]**: Valuation Stretch: Market implied 5Y FCF CAGR of 28.97% [LEDGER_0002] exceeds historical 3Y CAGR of 4.00% [LEDGER_0010].
  - *Verified Output:* `28.970104455947876` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 40] [LEDGER_0010]**: Valuation Stretch: Market implied 5Y FCF CAGR of 28.97% [LEDGER_0002] exceeds historical 3Y CAGR of 4.00% [LEDGER_0010].
  - *Verified Output:* `4.0` via `tools.calc.cagr`
  - *Source:* SEC 10-K / Annual Filings
- **[Line 41] [LEDGER_0008]**: Growth Dependency: Halving assumed growth rate drops fair value to $123.40 [LEDGER_0008].
  - *Verified Output:* `123.39874627773258` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 42] [LEDGER_0012]**: Inventory Divergence: Inventory growth diverged from revenue by -11.43% [LEDGER_0012].
  - *Verified Output:* `-11.42551178283274` via `tools.calc.working_capital`
  - *Source:* SEC 10-K / Annual Filings

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 43] [MODEL_MEMORY_TAGGED]**: Empirical Filing Note: [UNVERIFIED: model memory] Greater China net sales experienced modest deceleration in recent quarterly periods.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 44] [MODEL_MEMORY_TAGGED]**: Empirical Filing Note: [UNVERIFIED: model memory] Regulatory antitrust inquiries in EU and US pose long-term services gross margin headwinds.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*