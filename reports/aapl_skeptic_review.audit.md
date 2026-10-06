# Verification Audit Report
**Target Report:** `aapl_skeptic_review.md`  
**Audit Timestamp:** 2026-10-06T15:09:29.974778  
**Overall Status:** **PASS WITH FLAGS** (41 Confirmed, 0 Wrong, 2 Unverifiable)  

---

### ✅ 1. Confirmed Claims (41)
- **[Line 12] [LEDGER_0002]**: | Base Free Cash Flow | $98,767,000,000 | [LEDGER_0002] | Audited Statement of Cash Flows |
  - *Verified Output:* `98767000000` via `filing.cash_flow`
  - *Source:* Audited Cash Flow Statement
- **[Line 13] [LEDGER_0003]**: | Assumed 5Y FCF Growth Rate | 8.00% | [LEDGER_0003] | Analyst Thesis Model |
  - *Verified Output:* `8.0` via `thesis.assumption`
  - *Source:* Analyst Thesis Model Assumption
- **[Line 14] [LEDGER_0004]**: | Discount Rate (WACC) | 8.50% | [LEDGER_0004] | Cost of Capital Model |
  - *Verified Output:* `8.5` via `thesis.assumption`
  - *Source:* Cost of Capital Assumption
- **[Line 15] [LEDGER_0005]**: | Terminal Growth Rate | 2.50% | [LEDGER_0005] | Long-term GDP Baseline |
  - *Verified Output:* `2.5` via `thesis.assumption`
  - *Source:* Terminal Growth Assumption
- **[Line 16] [LEDGER_0006]**: | Shares Outstanding | 14,594,180,000 | [LEDGER_0006] | Market & Share Registry Data |
  - *Verified Output:* `14594180000.0` via `yfinance.quote`
  - *Source:* Share Registry / Market Data
- **[Line 17] [LEDGER_0007]**: | Net Debt | $0 | [LEDGER_0007] | Audited Balance Sheet |
  - *Verified Output:* `0.0` via `filing.balance_sheet`
  - *Source:* Audited Balance Sheet
- **[Line 23] [LEDGER_0001]**: Current Market Price: $332.77 USD [LEDGER_0001]
  - *Verified Output:* `332.7738` via `yfinance.quote`
  - *Source:* Market Quote (AAPL)
- **[Line 24] [LEDGER_0008]**: Implied 5-Year FCF CAGR (Reverse DCF): **28.96%** [LEDGER_0008]
  - *Verified Output:* `28.960567712783813` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 25] [LEDGER_0009]**: Baseline Fair Value (DCF): **$146.35** [LEDGER_0009]
  - *Verified Output:* `146.3459176168883` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 26] [LEDGER_0010]**: Stressed Fair Value (-200 bps Margin): **$137.19** [LEDGER_0010]
  - *Verified Output:* `137.19094378428977` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 27] [LEDGER_0011]**: Margin Stress Valuation Impact: **-6.26%** [LEDGER_0011]
  - *Verified Output:* `-6.255708380308141` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 28] [LEDGER_0012]**: Stressed Fair Value (+100 bps WACC): **$124.96** [LEDGER_0012]
  - *Verified Output:* `124.96477467593226` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 29] [LEDGER_0013]**: WACC Stress Valuation Impact: **-14.61%** [LEDGER_0013]
  - *Verified Output:* `-14.61000299094688` via `tools.calc.wacc_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 30] [LEDGER_0014]**: Stressed Fair Value (Half-Growth): **$123.40** [LEDGER_0014]
  - *Verified Output:* `123.39874627773258` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 31] [LEDGER_0015]**: Half-Growth Valuation Impact: **-15.68%** [LEDGER_0015]
  - *Verified Output:* `-15.680089826098174` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 39] [LEDGER_0008]**: | Valuation Feasibility | Implied CAGR 28.96% [LEDGER_0008] vs Hist -3.95% [LEDGER_0020] | [LEDGER_0008], [LEDGER_0020] | **FAIL** |
  - *Verified Output:* `28.960567712783813` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 39] [LEDGER_0020]**: | Valuation Feasibility | Implied CAGR 28.96% [LEDGER_0008] vs Hist -3.95% [LEDGER_0020] | [LEDGER_0008], [LEDGER_0020] | **FAIL** |
  - *Verified Output:* `-3.9450634871626145` via `tools.calc.cagr`
  - *Source:* tools.calc.metrics.cagr
- **[Line 39] [LEDGER_0008]**: | Valuation Feasibility | Implied CAGR 28.96% [LEDGER_0008] vs Hist -3.95% [LEDGER_0020] | [LEDGER_0008], [LEDGER_0020] | **FAIL** |
  - *Verified Output:* `28.960567712783813` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 39] [LEDGER_0020]**: | Valuation Feasibility | Implied CAGR 28.96% [LEDGER_0008] vs Hist -3.95% [LEDGER_0020] | [LEDGER_0008], [LEDGER_0020] | **FAIL** |
  - *Verified Output:* `-3.9450634871626145` via `tools.calc.cagr`
  - *Source:* tools.calc.metrics.cagr
- **[Line 40] [LEDGER_0011]**: | Margin Shock (-200 bps) | Impact -6.26% [LEDGER_0011] ($137.19 [LEDGER_0010]) | [LEDGER_0011], [LEDGER_0010] | **PASS** |
  - *Verified Output:* `-6.255708380308141` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 40] [LEDGER_0010]**: | Margin Shock (-200 bps) | Impact -6.26% [LEDGER_0011] ($137.19 [LEDGER_0010]) | [LEDGER_0011], [LEDGER_0010] | **PASS** |
  - *Verified Output:* `137.19094378428977` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 40] [LEDGER_0011]**: | Margin Shock (-200 bps) | Impact -6.26% [LEDGER_0011] ($137.19 [LEDGER_0010]) | [LEDGER_0011], [LEDGER_0010] | **PASS** |
  - *Verified Output:* `-6.255708380308141` via `tools.calc.margin_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 40] [LEDGER_0010]**: | Margin Shock (-200 bps) | Impact -6.26% [LEDGER_0011] ($137.19 [LEDGER_0010]) | [LEDGER_0011], [LEDGER_0010] | **PASS** |
  - *Verified Output:* `137.19094378428977` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 41] [LEDGER_0013]**: | WACC Shock (+100 bps) | Impact -14.61% [LEDGER_0013] ($124.96 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `-14.61000299094688` via `tools.calc.wacc_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 41] [LEDGER_0012]**: | WACC Shock (+100 bps) | Impact -14.61% [LEDGER_0013] ($124.96 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `124.96477467593226` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 41] [LEDGER_0013]**: | WACC Shock (+100 bps) | Impact -14.61% [LEDGER_0013] ($124.96 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `-14.61000299094688` via `tools.calc.wacc_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 41] [LEDGER_0012]**: | WACC Shock (+100 bps) | Impact -14.61% [LEDGER_0013] ($124.96 [LEDGER_0012]) | [LEDGER_0013], [LEDGER_0012] | **PASS** |
  - *Verified Output:* `124.96477467593226` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 42] [LEDGER_0014]**: | Half-Growth Stress | Stressed Fair Value $123.40 [LEDGER_0014] (-15.68% [LEDGER_0015]) | [LEDGER_0014], [LEDGER_0015] | **PASS** |
  - *Verified Output:* `123.39874627773258` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 42] [LEDGER_0015]**: | Half-Growth Stress | Stressed Fair Value $123.40 [LEDGER_0014] (-15.68% [LEDGER_0015]) | [LEDGER_0014], [LEDGER_0015] | **PASS** |
  - *Verified Output:* `-15.680089826098174` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 42] [LEDGER_0014]**: | Half-Growth Stress | Stressed Fair Value $123.40 [LEDGER_0014] (-15.68% [LEDGER_0015]) | [LEDGER_0014], [LEDGER_0015] | **PASS** |
  - *Verified Output:* `123.39874627773258` via `tools.calc.dcf`
  - *Source:* tools.calc.dcf.dcf
- **[Line 42] [LEDGER_0015]**: | Half-Growth Stress | Stressed Fair Value $123.40 [LEDGER_0014] (-15.68% [LEDGER_0015]) | [LEDGER_0014], [LEDGER_0015] | **PASS** |
  - *Verified Output:* `-15.680089826098174` via `tools.calc.growth_stress_impact`
  - *Source:* tools.calc.metrics
- **[Line 43] [LEDGER_0021]**: | Receivables Divergence | Divergence -6.80% [LEDGER_0021] | [LEDGER_0021] | **PASS** |
  - *Verified Output:* `-6.7955117828327385` via `tools.calc.working_capital`
  - *Source:* Annual Filings
- **[Line 43] [LEDGER_0021]**: | Receivables Divergence | Divergence -6.80% [LEDGER_0021] | [LEDGER_0021] | **PASS** |
  - *Verified Output:* `-6.7955117828327385` via `tools.calc.working_capital`
  - *Source:* Annual Filings
- **[Line 44] [LEDGER_0022]**: | Inventory Divergence | Divergence +6.44% [LEDGER_0022] | [LEDGER_0022] | **FAIL** |
  - *Verified Output:* `6.444488217167262` via `tools.calc.working_capital`
  - *Source:* Annual Filings
- **[Line 44] [LEDGER_0022]**: | Inventory Divergence | Divergence +6.44% [LEDGER_0022] | [LEDGER_0022] | **FAIL** |
  - *Verified Output:* `6.444488217167262` via `tools.calc.working_capital`
  - *Source:* Annual Filings
- **[Line 45] [LEDGER_0023]**: | Refinancing / Debt Risk | ST Debt / Cash = 36.44% [LEDGER_0023] | [LEDGER_0023] | **PASS** |
  - *Verified Output:* `36.44257422435962` via `tools.calc.liquidity`
  - *Source:* Annual Balance Sheet
- **[Line 45] [LEDGER_0023]**: | Refinancing / Debt Risk | ST Debt / Cash = 36.44% [LEDGER_0023] | [LEDGER_0023] | **PASS** |
  - *Verified Output:* `36.44257422435962` via `tools.calc.liquidity`
  - *Source:* Annual Balance Sheet
- **[Line 52] [ANALYSIS]**: [ANALYSIS] VULNERABLE: Found 2 quantitative failure(s) across 7 performed checks.
  - *Verified Output:* `ANALYST_DEDUCTION` via `analyst.reasoning`
  - *Source:* Report Author Analysis
- **[Line 53] [LEDGER_0008]**: Valuation Stretch: Market implied 5Y FCF CAGR of 28.96% [LEDGER_0008] exceeds historical CAGR of -3.95% [LEDGER_0020].
  - *Verified Output:* `28.960567712783813` via `tools.calc.reverse_dcf`
  - *Source:* tools.calc.dcf.reverse_dcf
- **[Line 53] [LEDGER_0020]**: Valuation Stretch: Market implied 5Y FCF CAGR of 28.96% [LEDGER_0008] exceeds historical CAGR of -3.95% [LEDGER_0020].
  - *Verified Output:* `-3.9450634871626145` via `tools.calc.cagr`
  - *Source:* tools.calc.metrics.cagr
- **[Line 54] [LEDGER_0022]**: Inventory Divergence: Inventory growth diverged from revenue by +6.44% [LEDGER_0022].
  - *Verified Output:* `6.444488217167262` via `tools.calc.working_capital`
  - *Source:* Annual Filings

---

### ❌ 2. Wrong / Discrepant Figures (0)
_None. No value discrepancies found._

---

### ⚠️ 3. Unverifiable / Failed Claims (2)
- **[Line 55] [MODEL_MEMORY_TAGGED]**: Unverified context: [UNVERIFIED: model memory] Greater China net sales experienced selective deceleration in recent quarterly periods.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).
- **[Line 56] [MODEL_MEMORY_TAGGED]**: Unverified context: [UNVERIFIED: model memory] Regulatory antitrust inquiries in EU and US pose long-term services gross margin headwinds.
  - *Failure Reason:* Declared model memory (unverified qualitative claim).

---
*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*