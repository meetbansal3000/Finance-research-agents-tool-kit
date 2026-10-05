"""
Skeptic Agent Engine (/agents/skeptic.py)
Adversarial research agent that tests the 3 core assumptions of an investment thesis
against mathematical sensitivity models, reverse DCF, and empirical counter-evidence.
Every cited number carries a ledger ID; unverified qualitative claims are tagged [UNVERIFIED: model memory].
"""

import os
import json
import datetime
from typing import Dict, Any, List, Optional
from tools.ledger import ProvenanceLedger
from tools.calc import (
    dcf, reverse_dcf, margin, yoy_growth, cagr,
    net_debt_to_ebitda, interest_coverage, fcf_yield
)

class SkepticAgent:
    def __init__(self, ledger: Optional[ProvenanceLedger] = None):
        self.ledger = ledger or ProvenanceLedger(run_id=f"skeptic_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")

    def evaluate_thesis(
        self,
        ticker: str,
        current_price: float,
        shares_outstanding: float,
        base_fcf: float,
        base_operating_margin: float,
        stated_growth_rate: float,
        net_debt: float = 0.0,
        wacc: float = 0.09,
        terminal_g: float = 0.025,
        empirical_counter_evidence: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Perform adversarial testing on top 3 thesis assumptions:
        1. Implied growth rate from current market price (Reverse DCF).
        2. Sensitivity of valuation to Margin compression (-200 bps).
        3. Sensitivity of valuation to Cost of Capital / WACC elevation (+100 bps).
        """
        # 0. Record Current Price & Base Metrics in Ledger
        l_price = self.ledger.record(
            tool="yfinance.quote",
            ticker=ticker,
            inputs={"ticker": ticker, "price": current_price},
            output=current_price,
            raw_value=current_price,
            source=f"Market Quote ({ticker})",
            notes="Current trading price"
        )
        
        # 1. Reverse DCF: Implied Growth Rate
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

        # 2. Baseline DCF Valuation with Analyst Stated Growth
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

        # 3. Stress Assumption A: Margin Compression (-200 bps)
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
            notes="Valuation impact percentage"
        )

        # 4. Stress Assumption B: WACC Elevation (+100 bps)
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
            notes="Valuation impact percentage"
        )

        # Evaluate if there is strong counter-evidence
        valuation_gap = ((current_price - base_fair_val) / base_fair_val) * 100.0
        has_empirical_flaws = bool(empirical_counter_evidence and len(empirical_counter_evidence) > 0)
        is_implied_growth_extreme = (implied_cagr > (stated_growth_rate * 100.0 + 5.0))
        
        # Build Adversarial Findings
        findings = []
        is_weak_thesis = False
        
        if is_implied_growth_extreme or valuation_gap > 20.0 or has_empirical_flaws:
            is_weak_thesis = True
            findings.append(f"Valuation Stretch: Current price of ${current_price:.2f} [{l_price}] implies a 5-year FCF CAGR of {implied_cagr:.2f}% [{l_implied}].")
            findings.append(f"Margin Sensitivity: A 2-percentage-point margin compression reduces fair value from ${base_fair_val:.2f} [{l_base_val}] to ${margin_stressed_val:.2f} [{l_margin_stress}] ({margin_impact_pct:+.2f}% [{l_margin_impact}] impact).")
            findings.append(f"Cost of Capital Sensitivity: Higher hurdle rate lowers fair value to ${wacc_stressed_val:.2f} [{l_wacc_stress}] ({wacc_impact_pct:+.2f}% [{l_wacc_impact}] impact).")
            if has_empirical_flaws:
                for item in empirical_counter_evidence:
                    findings.append(f"Empirical Headwind: [UNVERIFIED: model memory] {item}")
        else:
            findings.append("No strong counter-evidence found.")
            findings.append(f"Valuation Realism: Current price of ${current_price:.2f} [{l_price}] implies a modest 5-year FCF CAGR of {implied_cagr:.2f}% [{l_implied}].")
            findings.append(f"Balance Sheet & Cash Flow Resiliency: Fair value remains robust at ${margin_stressed_val:.2f} [{l_margin_stress}] even under margin contraction.")

        skeptic_report = f"""# Skeptic Adversarial Review: {ticker}
**Audit Date:** {datetime.datetime.now().strftime('%Y-%m-%d')}  
**Evaluator:** Antigravity Skeptic Agent  
**Thesis Verdict:** **{'VULNERABLE / STRETCHED' if is_weak_thesis else 'ROBUST / NO STRONG COUNTER-EVIDENCE FOUND'}**  

---

### 1. Stress Testing Top 3 Thesis Assumptions

1. **Market-Implied Growth Expectation (Reverse DCF)**:
   - Current Market Price: ${current_price:.2f} USD [{l_price}]
   - Implied 5-Year FCF CAGR: **{implied_cagr:.2f}%** [{l_implied}]

2. **Operating Margin Sensitivity (Downside Stress)**:
   - Baseline Fair Value: **${base_fair_val:.2f}** [{l_base_val}]
   - Stressed Fair Value: **${margin_stressed_val:.2f}** [{l_margin_stress}]
   - Valuation Downside Impact: **{margin_impact_pct:+.2f}%** [{l_margin_impact}]

3. **Interest Rate & WACC Sensitivity (Cost of Capital Elevation)**:
   - Baseline Fair Value: **${base_fair_val:.2f}** [{l_base_val}]
   - Stressed Fair Value: **${wacc_stressed_val:.2f}** [{l_wacc_stress}]
   - Valuation Downside Impact: **{wacc_impact_pct:+.2f}%** [{l_wacc_impact}]

---

### 2. Adversarial Findings & Conclusion

"""
        for item in findings:
            skeptic_report += f"- {item}\n"
            
        skeptic_report += "\n---\n*Generated by Antigravity Skeptic Agent. All numbers linked to Provenance Ledger.*"
        
        return {
            "ticker": ticker,
            "is_weak_thesis": is_weak_thesis,
            "implied_cagr": implied_cagr,
            "base_fair_val": base_fair_val,
            "margin_stressed_val": margin_stressed_val,
            "wacc_stressed_val": wacc_stressed_val,
            "markdown_report": skeptic_report,
            "ledger": self.ledger
        }
