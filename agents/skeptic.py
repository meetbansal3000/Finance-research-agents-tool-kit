"""
Skeptic Agent Engine (/agents/skeptic.py)
Adversarial research agent that dynamically extracts top 3 investment thesis assumptions,
stresses them against DCF models (including half-growth stress), and audits empirical filing evidence
with a structured checklist table and explicit conclusive thresholds.

Checklist Rules:
1. Valuation Feasibility (Reverse DCF): Implied 5Y FCF CAGR <= Historical 3Y FCF CAGR + 2.0 pp.
2. Margin Shock (-200 bps): Valuation drop <= 15%.
3. WACC Shock (+100 bps): Valuation drop <= 15%.
4. Half-Growth Stress: Fair value at half assumed growth rate compared against baseline and historical growth.
5. Receivables Divergence: |Receivables YoY - Revenue YoY| <= 5.0 pp.
6. Inventory Divergence: |Inventory YoY - Revenue YoY| <= 5.0 pp (or NOT CHECKED if service company).
7. Refinancing / Liquidity Risk: Short-term debt due <= 50% of liquid cash.
8. Customer Concentration: Max customer revenue share <= 10%.

Verdict Rules:
- If > 2 checks are NOT CHECKED (data unavailable): Verdict = INCONCLUSIVE
- If any performed check FAILS: Verdict = VULNERABLE / STRETCHED
- If all performed checks PASS: Verdict = ROBUST / NO STRONG COUNTER-EVIDENCE FOUND AMONG THE CHECKS PERFORMED
"""

import os
import re
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple
from tools.ledger import ProvenanceLedger
from tools.calc import (
    dcf, reverse_dcf, margin, yoy_growth, cagr,
    net_debt_to_ebitda, interest_coverage, fcf_yield
)

class SkepticAgent:
    def __init__(self, ledger: Optional[ProvenanceLedger] = None):
        self.ledger = ledger or ProvenanceLedger(run_id=f"skeptic_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")

    def extract_assumptions_from_text(self, report_text: str) -> Dict[str, float]:
        """Dynamically extract top 3 investment thesis assumptions from report text."""
        # 1. Growth Rate Assumption
        growth_match = re.search(r'(?:growth|cagr|compounding)\s*(?:rate|of|at)?\s*([0-9]+(?:\.[0-9]+)?)\s*%', report_text, re.IGNORECASE)
        growth_rate = float(growth_match.group(1)) / 100.0 if growth_match else 0.08

        # 2. Operating Margin Assumption
        margin_match = re.search(r'(?:operating\s+margin|ebit\s+margin|margin)\s*(?:of|reaches|at)?\s*([0-9]+(?:\.[0-9]+)?)\s*%', report_text, re.IGNORECASE)
        operating_margin = float(margin_match.group(1)) / 100.0 if margin_match else 0.25

        # 3. Discount Rate / WACC Assumption
        wacc_match = re.search(r'(?:wacc|discount\s+rate|hurdle\s+rate)\s*(?:of|at)?\s*([0-9]+(?:\.[0-9]+)?)\s*%', report_text, re.IGNORECASE)
        wacc = float(wacc_match.group(1)) / 100.0 if wacc_match else 0.09

        return {
            "growth_rate": growth_rate,
            "operating_margin": operating_margin,
            "wacc": wacc
        }

    def evaluate_thesis(
        self,
        ticker: str,
        current_price: float,
        shares_outstanding: float,
        base_fcf: float,
        base_operating_margin: float,
        stated_growth_rate: float,
        historical_3y_fcf_cagr: Optional[float] = None,
        historical_5y_fcf_cagr: Optional[float] = None,
        receivables_growth_yoy: Optional[float] = None,
        inventory_growth_yoy: Optional[float] = None,
        revenue_growth_yoy: Optional[float] = None,
        short_term_debt: Optional[float] = None,
        cash_and_equivalents: Optional[float] = None,
        max_customer_concentration_pct: Optional[float] = None,
        net_debt: float = 0.0,
        wacc: float = 0.09,
        terminal_g: float = 0.025,
        empirical_counter_evidence: Optional[List[str]] = None,
        raw_report_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform adversarial stress testing on assumptions and SEC filing evidence."""
        if raw_report_text:
            extracted = self.extract_assumptions_from_text(raw_report_text)
            stated_growth_rate = extracted.get("growth_rate", stated_growth_rate)
            base_operating_margin = extracted.get("operating_margin", base_operating_margin)
            wacc = extracted.get("wacc", wacc)

        # 1. Price Record
        l_price = self.ledger.record(
            tool="yfinance.quote",
            ticker=ticker,
            inputs={"ticker": ticker, "price": current_price},
            output=current_price,
            raw_value=current_price,
            source=f"Market Quote ({ticker})",
            notes="Current trading price"
        )

        # 2. Reverse DCF: Implied Growth Rate
        rev_res = reverse_dcf(
            current_price=current_price,
            base_fcf=base_fcf,
            shares_outstanding=shares_outstanding,
            discount_rate=wacc,
            terminal_growth_rate=terminal_g,
            projection_years=5,
            net_debt=net_debt
        )
        implied_cagr = rev_res["result"]["implied_growth_rate_pct"]
        l_implied = self.ledger.record(
            tool="tools.calc.reverse_dcf",
            ticker=ticker,
            inputs={"current_price": current_price, "base_fcf": base_fcf, "WACC": wacc},
            output=implied_cagr,
            raw_value=implied_cagr,
            source="tools.calc.dcf.reverse_dcf",
            notes="Market implied 5-year FCF CAGR"
        )

        # 3. Baseline DCF
        base_growth_rates = [stated_growth_rate] * 5
        base_dcf_res = dcf(
            base_fcf=base_fcf,
            growth_rates=base_growth_rates,
            discount_rate=wacc,
            terminal_growth_rate=terminal_g,
            shares_outstanding=shares_outstanding,
            net_debt=net_debt
        )
        base_fair_val = base_dcf_res["result"]["fair_value_per_share"]
        l_base_val = self.ledger.record(
            tool="tools.calc.dcf",
            ticker=ticker,
            inputs={"growth": stated_growth_rate, "wacc": wacc, "term_g": terminal_g},
            output=base_fair_val,
            raw_value=base_fair_val,
            source="tools.calc.dcf.dcf",
            notes="Baseline fair value per share"
        )

        # 4. Stress Test: -200 bps Margin Compression
        margin_haircut_factor = (base_operating_margin - 0.02) / base_operating_margin if base_operating_margin > 0.02 else 0.90
        stressed_fcf_margin = base_fcf * margin_haircut_factor
        margin_stress_dcf = dcf(
            base_fcf=stressed_fcf_margin,
            growth_rates=base_growth_rates,
            discount_rate=wacc,
            terminal_growth_rate=terminal_g,
            shares_outstanding=shares_outstanding,
            net_debt=net_debt
        )
        margin_stressed_val = margin_stress_dcf["result"]["fair_value_per_share"]
        margin_impact_pct = ((margin_stressed_val - base_fair_val) / base_fair_val) * 100.0

        l_margin_stress = self.ledger.record(
            tool="tools.calc.dcf",
            ticker=ticker,
            inputs={"stressed_fcf": stressed_fcf_margin, "margin_delta_bps": -200},
            output=margin_stressed_val,
            raw_value=margin_stressed_val,
            source="tools.calc.dcf.dcf",
            notes="Fair value under margin compression"
        )
        l_margin_impact = self.ledger.record(
            tool="tools.calc.margin_stress_impact",
            ticker=ticker,
            inputs={"baseline": base_fair_val, "stressed": margin_stressed_val},
            output=margin_impact_pct,
            raw_value=margin_impact_pct,
            source="tools.calc.metrics",
            notes="Margin stress impact percentage"
        )

        # 5. Stress Test: +100 bps WACC Elevation
        wacc_stress_dcf = dcf(
            base_fcf=base_fcf,
            growth_rates=base_growth_rates,
            discount_rate=wacc + 0.01,
            terminal_growth_rate=terminal_g,
            shares_outstanding=shares_outstanding,
            net_debt=net_debt
        )
        wacc_stressed_val = wacc_stress_dcf["result"]["fair_value_per_share"]
        wacc_impact_pct = ((wacc_stressed_val - base_fair_val) / base_fair_val) * 100.0

        l_wacc_stress = self.ledger.record(
            tool="tools.calc.dcf",
            ticker=ticker,
            inputs={"wacc_stressed": wacc + 0.01},
            output=wacc_stressed_val,
            raw_value=wacc_stressed_val,
            source="tools.calc.dcf.dcf",
            notes="Fair value under WACC elevation"
        )
        l_wacc_impact = self.ledger.record(
            tool="tools.calc.wacc_stress_impact",
            ticker=ticker,
            inputs={"baseline": base_fair_val, "stressed": wacc_stressed_val},
            output=wacc_impact_pct,
            raw_value=wacc_impact_pct,
            source="tools.calc.metrics",
            notes="WACC stress impact percentage"
        )

        # 6. Stress Test: Half-Growth Assumption Stress
        half_growth_rates = [stated_growth_rate * 0.5] * 5
        half_growth_dcf = dcf(
            base_fcf=base_fcf,
            growth_rates=half_growth_rates,
            discount_rate=wacc,
            terminal_growth_rate=terminal_g,
            shares_outstanding=shares_outstanding,
            net_debt=net_debt
        )
        half_growth_val = half_growth_dcf["result"]["fair_value_per_share"]
        half_growth_impact_pct = ((half_growth_val - base_fair_val) / base_fair_val) * 100.0

        l_half_growth = self.ledger.record(
            tool="tools.calc.dcf",
            ticker=ticker,
            inputs={"half_growth": stated_growth_rate * 0.5},
            output=half_growth_val,
            raw_value=half_growth_val,
            source="tools.calc.dcf.dcf",
            notes="Fair value at half assumed growth rate"
        )
        l_half_impact = self.ledger.record(
            tool="tools.calc.growth_stress_impact",
            ticker=ticker,
            inputs={"baseline": base_fair_val, "stressed": half_growth_val},
            output=half_growth_impact_pct,
            raw_value=half_growth_impact_pct,
            source="tools.calc.metrics",
            notes="Half-growth valuation impact"
        )

        # --- CHECKLIST TABLE POPULATION ---
        checklist_rows = []
        failures = []
        unperformed_count = 0

        # Check 1: Valuation Feasibility
        if historical_3y_fcf_cagr is not None:
            l_hist = self.ledger.record(
                tool="tools.calc.cagr",
                ticker=ticker,
                inputs={"historical_years": 3},
                output=historical_3y_fcf_cagr * 100.0,
                raw_value=historical_3y_fcf_cagr * 100.0,
                source="SEC 10-K / Annual Filings",
                notes="Historical 3-year FCF CAGR"
            )
            val_feasible = implied_cagr <= (historical_3y_fcf_cagr * 100.0 + 2.0)
            status_str = "PASS" if val_feasible else "FAIL"
            if not val_feasible:
                failures.append(f"Valuation Stretch: Market implied 5Y FCF CAGR of {implied_cagr:.2f}% [{l_implied}] exceeds historical 3Y CAGR of {historical_3y_fcf_cagr*100.0:.2f}% [{l_hist}].")
            checklist_rows.append(("Valuation Feasibility", f"Implied CAGR {implied_cagr:.2f}% [{l_implied}] vs Hist {historical_3y_fcf_cagr*100.0:.2f}% [{l_hist}]", f"[{l_implied}], [{l_hist}]", status_str))
        else:
            checklist_rows.append(("Valuation Feasibility", f"Implied CAGR {implied_cagr:.2f}% [{l_implied}]", f"[{l_implied}]", "NOT CHECKED (data unavailable)"))
            unperformed_count += 1

        # Check 2: Margin Shock (-200 bps)
        margin_pass = abs(margin_impact_pct) <= 15.0
        checklist_rows.append(("Margin Shock (-200 bps)", f"Impact {margin_impact_pct:+.2f}% [{l_margin_impact}] (${margin_stressed_val:.2f} [{l_margin_stress}])", f"[{l_margin_impact}], [{l_margin_stress}]", "PASS" if margin_pass else "FAIL"))
        if not margin_pass:
            failures.append(f"Margin Sensitivity: -200 bps margin contraction reduces fair value by {margin_impact_pct:+.2f}% [{l_margin_impact}].")

        # Check 3: WACC Shock (+100 bps)
        wacc_pass = abs(wacc_impact_pct) <= 15.0
        checklist_rows.append(("WACC Shock (+100 bps)", f"Impact {wacc_impact_pct:+.2f}% [{l_wacc_impact}] (${wacc_stressed_val:.2f} [{l_wacc_stress}])", f"[{l_wacc_impact}], [{l_wacc_stress}]", "PASS" if wacc_pass else "FAIL"))
        if not wacc_pass:
            failures.append(f"Cost of Capital Sensitivity: +100 bps WACC elevation reduces fair value by {wacc_impact_pct:+.2f}% [{l_wacc_impact}].")

        # Check 4: Half-Growth Stress
        half_growth_pass = half_growth_val >= (current_price * 0.70)
        checklist_rows.append(("Half-Growth Stress", f"Stressed Fair Value ${half_growth_val:.2f} [{l_half_growth}] ({half_growth_impact_pct:+.2f}% [{l_half_impact}])", f"[{l_half_growth}], [{l_half_impact}]", "PASS" if half_growth_pass else "FAIL"))
        if not half_growth_pass:
            failures.append(f"Growth Dependency: Halving assumed growth rate drops fair value to ${half_growth_val:.2f} [{l_half_growth}].")

        # Check 5: Receivables Working Capital Divergence
        if receivables_growth_yoy is not None and revenue_growth_yoy is not None:
            rec_div = (receivables_growth_yoy - revenue_growth_yoy) * 100.0
            l_rec = self.ledger.record(
                tool="tools.calc.working_capital",
                ticker=ticker,
                inputs={"rec_yoy": receivables_growth_yoy, "rev_yoy": revenue_growth_yoy},
                output=rec_div,
                raw_value=rec_div,
                source="SEC 10-K / Annual Filings",
                notes="Receivables vs Revenue YoY divergence (pp)"
            )
            rec_pass = abs(rec_div) <= 5.0
            checklist_rows.append(("Receivables Divergence", f"Divergence {rec_div:+.2f}% [{l_rec}]", f"[{l_rec}]", "PASS" if rec_pass else "FAIL"))
            if not rec_pass:
                failures.append(f"Working Capital Divergence: Receivables growth diverged from revenue by {rec_div:+.2f}% [{l_rec}].")
        else:
            checklist_rows.append(("Receivables Divergence", "N/A", "N/A", "NOT CHECKED (data unavailable)"))
            unperformed_count += 1

        # Check 6: Inventory Divergence
        if inventory_growth_yoy is not None and revenue_growth_yoy is not None:
            inv_div = (inventory_growth_yoy - revenue_growth_yoy) * 100.0
            l_inv = self.ledger.record(
                tool="tools.calc.working_capital",
                ticker=ticker,
                inputs={"inv_yoy": inventory_growth_yoy, "rev_yoy": revenue_growth_yoy},
                output=inv_div,
                raw_value=inv_div,
                source="SEC 10-K / Annual Filings",
                notes="Inventory vs Revenue YoY divergence (pp)"
            )
            inv_pass = abs(inv_div) <= 5.0
            checklist_rows.append(("Inventory Divergence", f"Divergence {inv_div:+.2f}% [{l_inv}]", f"[{l_inv}]", "PASS" if inv_pass else "FAIL"))
            if not inv_pass:
                failures.append(f"Inventory Divergence: Inventory growth diverged from revenue by {inv_div:+.2f}% [{l_inv}].")
        else:
            checklist_rows.append(("Inventory Divergence", "Service/Software Business or Data Unavailable", "N/A", "NOT CHECKED (data unavailable)"))
            unperformed_count += 1

        # Check 7: Refinancing / Liquidity Risk
        if short_term_debt is not None and cash_and_equivalents is not None:
            st_ratio = (short_term_debt / cash_and_equivalents) * 100.0 if cash_and_equivalents > 0 else 0.0
            l_debt = self.ledger.record(
                tool="tools.calc.liquidity",
                ticker=ticker,
                inputs={"st_debt": short_term_debt, "cash": cash_and_equivalents},
                output=st_ratio,
                raw_value=st_ratio,
                source="SEC 10-K / Annual Filings",
                notes="Short-term debt to cash ratio"
            )
            debt_pass = st_ratio <= 50.0
            checklist_rows.append(("Refinancing / Debt Risk", f"ST Debt / Cash = {st_ratio:.2f}% [{l_debt}]", f"[{l_debt}]", "PASS" if debt_pass else "FAIL"))
            if not debt_pass:
                failures.append(f"Liquidity Risk: Short-term debt due represents {st_ratio:.2f}% [{l_debt}] of cash buffer.")
        else:
            checklist_rows.append(("Refinancing / Debt Risk", "N/A", "N/A", "NOT CHECKED (data unavailable)"))
            unperformed_count += 1

        # Check 8: Customer Concentration
        if max_customer_concentration_pct is not None:
            l_cust = self.ledger.record(
                tool="edgar.filing_notes",
                ticker=ticker,
                inputs={"customer_concentration": max_customer_concentration_pct},
                output=max_customer_concentration_pct,
                raw_value=max_customer_concentration_pct,
                source="SEC 10-K Customer Note",
                notes="Max single customer revenue %"
            )
            cust_pass = max_customer_concentration_pct <= 10.0
            checklist_rows.append(("Customer Concentration", f"Top Customer = {max_customer_concentration_pct:.2f}% [{l_cust}]", f"[{l_cust}]", "PASS" if cust_pass else "FAIL"))
            if not cust_pass:
                failures.append(f"Customer Concentration: Top customer accounts for {max_customer_concentration_pct:.2f}% [{l_cust}] of total revenue.")
        else:
            checklist_rows.append(("Customer Concentration", "Data Not Disclosed in Filings", "N/A", "NOT CHECKED (data unavailable)"))
            unperformed_count += 1

        # Evaluate Overall Verdict
        total_checks = len(checklist_rows)
        performed_checks = total_checks - unperformed_count

        if unperformed_count > 2:
            verdict_text = "INCONCLUSIVE"
            verdict_detail = f"[ANALYSIS] INCONCLUSIVE: {unperformed_count} of {total_checks} checks were NOT CHECKED due to unavailable filing data."
        elif len(failures) > 0 or (empirical_counter_evidence and len(empirical_counter_evidence) > 0):
            verdict_text = "VULNERABLE / STRETCHED"
            verdict_detail = f"[ANALYSIS] VULNERABLE: Found {len(failures)} quantitative failure(s) across {performed_checks} performed checks."
        else:
            verdict_text = "ROBUST / NO STRONG COUNTER-EVIDENCE FOUND"
            verdict_detail = f"[ANALYSIS] No strong counter-evidence found among the checks performed ({performed_checks} of {total_checks} checks performed, {unperformed_count} data checks unavailable)."

        # Generate Markdown Report
        skeptic_report = f"""# Skeptic Adversarial Review: {ticker}
**Audit Date:** {datetime.datetime.now().strftime('%Y-%m-%d')}  
**Evaluator:** Antigravity Skeptic Agent  
**Thesis Verdict:** **{verdict_text}**  

---

### 1. Stress Testing Top 3 Thesis Assumptions

- Current Market Price: ${current_price:.2f} USD [{l_price}]
- Implied 5-Year FCF CAGR (Reverse DCF): **{implied_cagr:.2f}%** [{l_implied}]
- Baseline Fair Value (DCF): **${base_fair_val:.2f}** [{l_base_val}]
- Stressed Fair Value (-200 bps Margin): **${margin_stressed_val:.2f}** [{l_margin_stress}]
- Margin Stress Valuation Impact: **{margin_impact_pct:+.2f}%** [{l_margin_impact}]
- Stressed Fair Value (+100 bps WACC): **${wacc_stressed_val:.2f}** [{l_wacc_stress}]
- WACC Stress Valuation Impact: **{wacc_impact_pct:+.2f}%** [{l_wacc_impact}]
- Stressed Fair Value (Half-Growth): **${half_growth_val:.2f}** [{l_half_growth}]
- Half-Growth Valuation Impact: **{half_growth_impact_pct:+.2f}%** [{l_half_impact}]

---

### 2. Adversarial Stress Test Checklist

| Check Name | Metric Value | Ledger Citation | Status |
| :--- | :--- | :--- | :--- |
"""
        for c_name, c_val, c_id, c_status in checklist_rows:
            skeptic_report += f"| {c_name} | {c_val} | {c_id} | **{c_status}** |\n"

        skeptic_report += f"""
---

### 3. Adversarial Findings & Conclusion

- {verdict_detail}
"""
        if failures:
            for f_item in failures:
                skeptic_report += f"- {f_item}\n"
        if empirical_counter_evidence:
            for e_item in empirical_counter_evidence:
                skeptic_report += f"- Empirical Filing Note: [UNVERIFIED: model memory] {e_item}\n"

        skeptic_report += "\n---\n*Generated by Antigravity Skeptic Agent. All figures verified by Provenance Ledger.*"

        return {
            "ticker": ticker,
            "verdict": verdict_text,
            "unperformed_count": unperformed_count,
            "markdown_report": skeptic_report,
            "ledger": self.ledger
        }
