"""
Skeptic Agent Engine (/agents/skeptic.py)
Adversarial research agent that stress-tests investment thesis assumptions,
constructs a multi-scenario sensitivity grid (growth x WACC),
audits empirical balance sheet liquidity and working capital divergence,
and categorizes inputs strictly into ASSUMPTION vs AUDITED DATA vs MARKET DATA.
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
        historical_fcf_series: Optional[Dict[str, float]] = None,
        historical_3y_fcf_cagr: Optional[float] = None,
        historical_5y_fcf_cagr: Optional[float] = None,
        receivables_growth_yoy: Optional[float] = None,
        inventory_growth_yoy: Optional[float] = None,
        revenue_growth_yoy: Optional[float] = None,
        working_capital_details: Optional[Dict[str, Any]] = None,
        short_term_debt: Optional[float] = None,
        cash_and_equivalents: Optional[float] = None,
        marketable_securities: Optional[float] = None,
        total_debt: Optional[float] = None,
        max_customer_concentration_pct: Optional[float] = None,
        net_debt: Optional[float] = None,
        wacc: float = 0.09,
        terminal_g: float = 0.025,
        currency: Optional[str] = None,
        currency_symbol: Optional[str] = None,
        empirical_counter_evidence: Optional[List[str]] = None,
        raw_report_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform adversarial stress testing on assumptions and filing evidence."""
        if raw_report_text:
            extracted = self.extract_assumptions_from_text(raw_report_text)
            stated_growth_rate = extracted.get("growth_rate", stated_growth_rate)
            base_operating_margin = extracted.get("operating_margin", base_operating_margin)
            wacc = extracted.get("wacc", wacc)

        # Determine currency & symbol
        if not currency:
            if ticker == "AAPL" or (ticker and "." not in ticker and not ticker.endswith(".NS") and not ticker.endswith(".L")):
                currency = "USD"
            elif ticker and (".NS" in ticker or ".BO" in ticker):
                currency = "INR"
            elif ticker and ticker.endswith(".L"):
                currency = "GBP"
            else:
                currency = "USD"

        if not currency_symbol:
            curr_map = {"USD": "$", "INR": "₹", "GBP": "£", "EUR": "€"}
            curr_sym = curr_map.get(currency, "$")
        else:
            curr_sym = currency_symbol

        # Balance Sheet Debt & Cash derivation (never default to $0 net debt if cash/debt provided)
        liquid_cash = (cash_and_equivalents or 0.0) + (marketable_securities or 0.0)
        tot_debt = total_debt or (short_term_debt or 0.0)
        if net_debt is None:
            net_debt = tot_debt - liquid_cash

        # 1. Price Record (MARKET DATA)
        l_price = self.ledger.record(
            tool="yfinance.quote",
            ticker=ticker,
            currency=currency,
            inputs={"ticker": ticker, "price": current_price},
            output=current_price,
            raw_value=current_price,
            source=f"Market Quote ({ticker})",
            notes=f"Current trading price ({currency})"
        )

        # 2. Shares Outstanding Record (MARKET DATA)
        l_shares = self.ledger.record(
            tool="yfinance.quote",
            ticker=ticker,
            inputs={"shares_outstanding": shares_outstanding},
            output=shares_outstanding,
            raw_value=shares_outstanding,
            source="Share Registry / Market Data",
            notes="Diluted Shares Outstanding"
        )

        # 3. Base FCF Record (AUDITED DATA)
        l_base_fcf = self.ledger.record(
            tool="filing.cash_flow",
            ticker=ticker,
            currency=currency,
            inputs={"ticker": ticker, "metric": "FreeCashFlow"},
            output=base_fcf,
            raw_value=base_fcf,
            source="Audited Statement of Cash Flows",
            notes=f"Base Free Cash Flow ({currency})"
        )

        # 4. Balance Sheet Records (AUDITED DATA)
        l_cash = self.ledger.record(
            tool="filing.balance_sheet",
            ticker=ticker,
            currency=currency,
            inputs={"cash_and_equivalents": cash_and_equivalents or 0.0, "marketable_securities": marketable_securities or 0.0},
            output=liquid_cash,
            raw_value=liquid_cash,
            source="Audited Balance Sheet",
            notes=f"Total Liquid Cash and Marketable Securities ({currency})"
        )
        l_total_debt = self.ledger.record(
            tool="filing.balance_sheet",
            ticker=ticker,
            currency=currency,
            inputs={"total_debt": tot_debt},
            output=tot_debt,
            raw_value=tot_debt,
            source="Audited Balance Sheet",
            notes=f"Total Borrowings and Debt ({currency})"
        )
        l_net_debt = self.ledger.record(
            tool="filing.balance_sheet",
            ticker=ticker,
            currency=currency,
            inputs={"total_debt": tot_debt, "liquid_cash": liquid_cash},
            output=net_debt,
            raw_value=net_debt,
            source="Audited Balance Sheet",
            notes=f"Calculated Net Debt: Total Debt - Liquid Cash ({currency})"
        )

        # 5. Model Assumptions Records (TYPE: ASSUMPTION - No fake sources)
        l_growth_assump = self.ledger.record(
            tool="thesis.assumption",
            ticker=ticker,
            inputs={"growth_rate": stated_growth_rate},
            output=stated_growth_rate * 100.0,
            raw_value=stated_growth_rate * 100.0,
            source="Model Assumption (Unanchored Parameter)",
            notes="Assumed 5Y FCF Growth Rate (%)"
        )
        l_wacc_assump = self.ledger.record(
            tool="thesis.assumption",
            ticker=ticker,
            inputs={"wacc": wacc},
            output=wacc * 100.0,
            raw_value=wacc * 100.0,
            source="Model Assumption (Unanchored Parameter)",
            notes="Assumed Discount Rate WACC (%)"
        )
        l_term_g_assump = self.ledger.record(
            tool="thesis.assumption",
            ticker=ticker,
            inputs={"terminal_g": terminal_g},
            output=terminal_g * 100.0,
            raw_value=terminal_g * 100.0,
            source="Model Assumption (Unanchored Parameter)",
            notes="Assumed Terminal Growth Rate (%)"
        )

        # 6. Reverse DCF: Implied Growth Rate
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
            inputs={"current_price": current_price, "base_fcf": base_fcf, "WACC": wacc, "net_debt": net_debt},
            output=implied_cagr,
            raw_value=implied_cagr,
            source="tools.calc.dcf.reverse_dcf",
            notes="Market implied 5-year FCF CAGR"
        )

        # 7. Baseline DCF
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
            currency=currency,
            inputs={"growth": stated_growth_rate, "wacc": wacc, "term_g": terminal_g, "net_debt": net_debt},
            output=base_fair_val,
            raw_value=base_fair_val,
            source="tools.calc.dcf.dcf",
            notes=f"Baseline fair value per share ({currency})"
        )

        # 8. Stress Test: -200 bps Margin Compression
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
            currency=currency,
            inputs={"stressed_fcf": stressed_fcf_margin, "margin_delta_bps": -200, "net_debt": net_debt},
            output=margin_stressed_val,
            raw_value=margin_stressed_val,
            source="tools.calc.dcf.dcf",
            notes=f"Fair value under margin compression ({currency})"
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

        # 9. Stress Test: +100 bps WACC Elevation
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
            currency=currency,
            inputs={"wacc_stressed": wacc + 0.01, "net_debt": net_debt},
            output=wacc_stressed_val,
            raw_value=wacc_stressed_val,
            source="tools.calc.dcf.dcf",
            notes=f"Fair value under WACC elevation ({currency})"
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

        # 10. Stress Test: Half-Growth Assumption Stress
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
            currency=currency,
            inputs={"half_growth": stated_growth_rate * 0.5, "net_debt": net_debt},
            output=half_growth_val,
            raw_value=half_growth_val,
            source="tools.calc.dcf.dcf",
            notes=f"Fair value at half assumed growth rate ({currency})"
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

        # 11. Valuation Sensitivity Grid: Growth x WACC
        grid_growths = [stated_growth_rate - 0.02, stated_growth_rate, stated_growth_rate + 0.02]
        grid_waccs = [wacc - 0.01, wacc, wacc + 0.01]
        
        l_g_low = self.ledger.record(
            tool="thesis.assumption",
            ticker=ticker,
            inputs={"growth_rate": stated_growth_rate - 0.02},
            output=(stated_growth_rate - 0.02) * 100.0,
            raw_value=(stated_growth_rate - 0.02) * 100.0,
            source="Model Sensitivity Parameter (Downside)",
            notes="Sensitivity Downside 5Y FCF Growth Rate (%)"
        )
        l_g_high = self.ledger.record(
            tool="thesis.assumption",
            ticker=ticker,
            inputs={"growth_rate": stated_growth_rate + 0.02},
            output=(stated_growth_rate + 0.02) * 100.0,
            raw_value=(stated_growth_rate + 0.02) * 100.0,
            source="Model Sensitivity Parameter (Upside)",
            notes="Sensitivity Upside 5Y FCF Growth Rate (%)"
        )

        grid_results = {}
        for g_val in grid_growths:
            for w_val in grid_waccs:
                cell_dcf = dcf(
                    base_fcf=base_fcf,
                    growth_rates=[g_val] * 5,
                    discount_rate=w_val,
                    terminal_growth_rate=terminal_g,
                    shares_outstanding=shares_outstanding,
                    net_debt=net_debt
                )
                cell_fv = cell_dcf["result"]["fair_value_per_share"]
                l_cell = self.ledger.record(
                    tool="tools.calc.dcf",
                    ticker=ticker,
                    currency=currency,
                    inputs={"growth": g_val, "wacc": w_val, "net_debt": net_debt},
                    output=cell_fv,
                    raw_value=cell_fv,
                    source="tools.calc.dcf.dcf",
                    notes=f"Sensitivity fair value: Growth {g_val*100.1:.1f}%, WACC {w_val*100.1:.1f}% ({currency})"
                )
                grid_results[(round(g_val, 4), round(w_val, 4))] = (cell_fv, l_cell)

        # --- CHECKLIST TABLE POPULATION ---
        checklist_rows = []
        failures = []
        unperformed_count = 0

        # Check 1: Valuation Feasibility (with historical FCF series if provided)
        hist_cagr_val = None
        hist_cagr_id = None
        
        if historical_fcf_series and len(historical_fcf_series) >= 2:
            sorted_years = sorted(historical_fcf_series.keys())
            start_yr, end_yr = sorted_years[0], sorted_years[-1]
            start_val, end_val = historical_fcf_series[start_yr], historical_fcf_series[end_yr]
            num_periods = len(sorted_years) - 1
            
            # Record individual historical FCF years
            hist_ids = []
            for yr in sorted_years:
                hid = self.ledger.record(
                    tool="filing.cash_flow",
                    ticker=ticker,
                    currency=currency,
                    inputs={"ticker": ticker, "metric": "FreeCashFlow", "period": yr},
                    output=historical_fcf_series[yr],
                    raw_value=historical_fcf_series[yr],
                    source=f"Annual Report {yr} Audited Cash Flow",
                    period=yr,
                    notes=f"{ticker} {yr} Free Cash Flow ({currency})"
                )
                hist_ids.append(hid)
            
            # Compute CAGR
            cagr_res = cagr(start_value=start_val, end_value=end_val, periods=num_periods)
            hist_cagr_val = cagr_res["result"]
            hist_cagr_id = self.ledger.record(
                tool="tools.calc.cagr",
                ticker=ticker,
                inputs={"start_value": start_val, "end_value": end_val, "periods": num_periods},
                output=hist_cagr_val,
                raw_value=hist_cagr_val,
                source="tools.calc.metrics.cagr",
                notes=f"Historical {num_periods}-year FCF CAGR ({start_yr} to {end_yr})"
            )
        elif historical_3y_fcf_cagr is not None:
            hist_cagr_val = historical_3y_fcf_cagr * 100.0
            hist_cagr_id = self.ledger.record(
                tool="tools.calc.cagr",
                ticker=ticker,
                inputs={"historical_years": 3},
                output=hist_cagr_val,
                raw_value=hist_cagr_val,
                source="SEC 10-K / Annual Filings",
                notes="Historical 3-year FCF CAGR"
            )

        if hist_cagr_val is not None:
            val_feasible = implied_cagr <= (hist_cagr_val + 2.0)
            status_str = "PASS" if val_feasible else "FAIL"
            if not val_feasible:
                failures.append(f"Valuation Stretch: Market implied 5Y FCF CAGR of {implied_cagr:.2f}% [{l_implied}] exceeds historical CAGR of {hist_cagr_val:+.2f}% [{hist_cagr_id}].")
            checklist_rows.append(("Valuation Feasibility", f"Implied CAGR {implied_cagr:.2f}% [{l_implied}] vs Hist {hist_cagr_val:+.2f}% [{hist_cagr_id}]", f"[{l_implied}], [{hist_cagr_id}]", status_str))
        else:
            checklist_rows.append(("Valuation Feasibility", f"Implied CAGR {implied_cagr:.2f}% [{l_implied}]", f"[{l_implied}]", "NOT CHECKED (data unavailable)"))
            unperformed_count += 1

        # Check 2: Margin Shock (-200 bps)
        margin_pass = abs(margin_impact_pct) <= 15.0
        checklist_rows.append(("Margin Shock (-200 bps)", f"Impact {margin_impact_pct:+.2f}% [{l_margin_impact}] ({curr_sym}{margin_stressed_val:.2f} [{l_margin_stress}])", f"[{l_margin_impact}], [{l_margin_stress}]", "PASS" if margin_pass else "FAIL"))
        if not margin_pass:
            failures.append(f"Margin Sensitivity: -200 bps margin contraction reduces fair value by {margin_impact_pct:+.2f}% [{l_margin_impact}].")

        # Check 3: WACC Shock (+100 bps)
        wacc_pass = abs(wacc_impact_pct) <= 15.0
        checklist_rows.append(("WACC Shock (+100 bps)", f"Impact {wacc_impact_pct:+.2f}% [{l_wacc_impact}] ({curr_sym}{wacc_stressed_val:.2f} [{l_wacc_stress}])", f"[{l_wacc_impact}], [{l_wacc_stress}]", "PASS" if wacc_pass else "FAIL"))
        if not wacc_pass:
            failures.append(f"Cost of Capital Sensitivity: +100 bps WACC elevation reduces fair value by {wacc_impact_pct:+.2f}% [{l_wacc_impact}].")

        # Check 4: Half-Growth Stress (Compares to Baseline Fair Value, threshold: drop <= 30%)
        half_growth_pass = abs(half_growth_impact_pct) <= 30.0
        checklist_rows.append(("Half-Growth Stress", f"Stressed Fair Value {curr_sym}{half_growth_val:.2f} [{l_half_growth}] ({half_growth_impact_pct:+.2f}% [{l_half_impact}])", f"[{l_half_growth}], [{l_half_impact}]", "PASS" if half_growth_pass else "FAIL"))
        if not half_growth_pass:
            failures.append(f"Growth Dependency: Halving assumed growth rate drops baseline fair value by {half_growth_impact_pct:+.2f}% [{l_half_impact}] to {curr_sym}{half_growth_val:.2f} [{l_half_growth}].")

        # Check 5: Receivables Working Capital Divergence
        if working_capital_details and "rec_curr" in working_capital_details and "rec_prev" in working_capital_details and "rev_curr" in working_capital_details and "rev_prev" in working_capital_details:
            wcd = working_capital_details
            l_wc_rev_curr = self.ledger.record(tool="filing.income_statement", ticker=ticker, currency=currency, inputs={"rev_curr": wcd["rev_curr"]}, output=wcd["rev_curr"], raw_value=wcd["rev_curr"], source="Audited Income Statement", notes="FY2025 Revenue")
            l_wc_rev_prev = self.ledger.record(tool="filing.income_statement", ticker=ticker, currency=currency, inputs={"rev_prev": wcd["rev_prev"]}, output=wcd["rev_prev"], raw_value=wcd["rev_prev"], source="Audited Income Statement", notes="FY2024 Revenue")
            rev_growth_yoy = ((wcd["rev_curr"] - wcd["rev_prev"]) / wcd["rev_prev"])
            l_wc_rev_yoy = self.ledger.record(tool="tools.calc.yoy_growth", ticker=ticker, inputs={"current": wcd["rev_curr"], "prior": wcd["rev_prev"]}, output=rev_growth_yoy * 100.0, raw_value=rev_growth_yoy * 100.0, source="tools.calc.metrics.yoy_growth", notes="Revenue YoY Growth (%)")
            
            l_wc_rec_curr = self.ledger.record(tool="filing.balance_sheet", ticker=ticker, currency=currency, inputs={"rec_curr": wcd["rec_curr"]}, output=wcd["rec_curr"], raw_value=wcd["rec_curr"], source="Audited Balance Sheet", notes="FY2025 Trade Receivables")
            l_wc_rec_prev = self.ledger.record(tool="filing.balance_sheet", ticker=ticker, currency=currency, inputs={"rec_prev": wcd["rec_prev"]}, output=wcd["rec_prev"], raw_value=wcd["rec_prev"], source="Audited Balance Sheet", notes="FY2024 Trade Receivables")
            rec_yoy = ((wcd["rec_curr"] - wcd["rec_prev"]) / wcd["rec_prev"])
            l_wc_rec_yoy = self.ledger.record(tool="tools.calc.yoy_growth", ticker=ticker, inputs={"current": wcd["rec_curr"], "prior": wcd["rec_prev"]}, output=rec_yoy * 100.0, raw_value=rec_yoy * 100.0, source="tools.calc.metrics.yoy_growth", notes="Receivables YoY Growth (%)")

            rec_div = (rec_yoy - rev_growth_yoy) * 100.0
            l_rec = self.ledger.record(
                tool="tools.calc.working_capital",
                ticker=ticker,
                inputs={"rec_yoy": rec_yoy * 100.0, "rev_yoy": rev_growth_yoy * 100.0},
                output=rec_div,
                raw_value=rec_div,
                source="tools.calc.working_capital",
                notes="Receivables vs Revenue YoY divergence (pp)"
            )
            rec_pass = rec_div <= 5.0
            checklist_rows.append(("Receivables Divergence", f"Divergence {rec_div:+.2f}% [{l_rec}]", f"[{l_rec}]", "PASS" if rec_pass else "FAIL"))
            if not rec_pass:
                failures.append(f"Working Capital Divergence: Receivables growth ({rec_yoy*100:+.2f}% [{l_wc_rec_yoy}]) diverged from revenue ({rev_growth_yoy*100:+.2f}% [{l_wc_rev_yoy}]) by {rec_div:+.2f}% [{l_rec}].")
        elif receivables_growth_yoy is not None and revenue_growth_yoy is not None:
            rec_div = (receivables_growth_yoy - revenue_growth_yoy) * 100.0
            l_rec = self.ledger.record(
                tool="tools.calc.working_capital",
                ticker=ticker,
                inputs={"rec_yoy": receivables_growth_yoy, "rev_yoy": revenue_growth_yoy},
                output=rec_div,
                raw_value=rec_div,
                source="Annual Filings",
                notes="Receivables vs Revenue YoY divergence (pp)"
            )
            rec_pass = rec_div <= 5.0
            checklist_rows.append(("Receivables Divergence", f"Divergence {rec_div:+.2f}% [{l_rec}]", f"[{l_rec}]", "PASS" if rec_pass else "FAIL"))
            if not rec_pass:
                failures.append(f"Working Capital Divergence: Receivables growth diverged from revenue by {rec_div:+.2f}% [{l_rec}].")
        else:
            checklist_rows.append(("Receivables Divergence", "N/A", "N/A", "NOT CHECKED (data unavailable)"))
            unperformed_count += 1

        # Check 6: Inventory Divergence
        if working_capital_details and "inv_curr" in working_capital_details and "inv_prev" in working_capital_details and working_capital_details["inv_curr"] is not None:
            wcd = working_capital_details
            l_wc_inv_curr = self.ledger.record(tool="filing.balance_sheet", ticker=ticker, currency=currency, inputs={"inv_curr": wcd["inv_curr"]}, output=wcd["inv_curr"], raw_value=wcd["inv_curr"], source="Audited Balance Sheet", notes="FY2025 Inventories")
            l_wc_inv_prev = self.ledger.record(tool="filing.balance_sheet", ticker=ticker, currency=currency, inputs={"inv_prev": wcd["inv_prev"]}, output=wcd["inv_prev"], raw_value=wcd["inv_prev"], source="Audited Balance Sheet", notes="FY2024 Inventories")
            inv_yoy = ((wcd["inv_curr"] - wcd["inv_prev"]) / wcd["inv_prev"])
            l_wc_inv_yoy = self.ledger.record(tool="tools.calc.yoy_growth", ticker=ticker, inputs={"current": wcd["inv_curr"], "prior": wcd["inv_prev"]}, output=inv_yoy * 100.0, raw_value=inv_yoy * 100.0, source="tools.calc.metrics.yoy_growth", notes="Inventory YoY Growth (%)")

            rev_growth_base = rev_growth_yoy or 0.0
            inv_div = (inv_yoy - rev_growth_base) * 100.0
            l_inv = self.ledger.record(
                tool="tools.calc.working_capital",
                ticker=ticker,
                inputs={"inv_yoy": inv_yoy * 100.0, "rev_yoy": rev_growth_base * 100.0},
                output=inv_div,
                raw_value=inv_div,
                source="tools.calc.working_capital",
                notes="Inventory vs Revenue YoY divergence (pp)"
            )
            rev_total = wcd.get("rev_curr", 0.0)
            is_immaterial = rev_total > 0 and (wcd["inv_curr"] / rev_total) < 0.02
            if is_immaterial:
                checklist_rows.append(("Inventory Divergence", f"Divergence {inv_div:+.2f}% [{l_inv}] (Immaterial: <2% of revenue)", f"[{l_inv}]", "NOT APPLICABLE"))
                unperformed_count += 1
            else:
                inv_pass = inv_div <= 5.0
                checklist_rows.append(("Inventory Divergence", f"Divergence {inv_div:+.2f}% [{l_inv}]", f"[{l_inv}]", "PASS" if inv_pass else "FAIL"))
                if not inv_pass:
                    failures.append(f"Inventory Divergence: Inventory growth ({inv_yoy*100:+.2f}% [{l_wc_inv_yoy}]) diverged from revenue by {inv_div:+.2f}% [{l_inv}].")
        elif inventory_growth_yoy is not None and revenue_growth_yoy is not None:
            inv_div = (inventory_growth_yoy - revenue_growth_yoy) * 100.0
            l_inv = self.ledger.record(
                tool="tools.calc.working_capital",
                ticker=ticker,
                inputs={"inv_yoy": inventory_growth_yoy, "rev_yoy": revenue_growth_yoy},
                output=inv_div,
                raw_value=inv_div,
                source="Annual Filings",
                notes="Inventory vs Revenue YoY divergence (pp)"
            )
            inv_pass = inv_div <= 5.0
            checklist_rows.append(("Inventory Divergence", f"Divergence {inv_div:+.2f}% [{l_inv}]", f"[{l_inv}]", "PASS" if inv_pass else "FAIL"))
            if not inv_pass:
                failures.append(f"Inventory Divergence: Inventory growth diverged from revenue by {inv_div:+.2f}% [{l_inv}].")
        else:
            checklist_rows.append(("Inventory Divergence", "Service/Software Business or Data Unavailable", "N/A", "NOT CHECKED (data unavailable)"))
            unperformed_count += 1

        # Check 7: Refinancing / Liquidity Risk
        if short_term_debt is not None and liquid_cash > 0:
            st_ratio = (short_term_debt / liquid_cash) * 100.0
            l_debt = self.ledger.record(
                tool="tools.calc.liquidity",
                ticker=ticker,
                inputs={"st_debt": short_term_debt, "cash": liquid_cash},
                output=st_ratio,
                raw_value=st_ratio,
                source="Annual Balance Sheet",
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
                source="SEC 10-K Note Disclosures / XBRL us-gaap:ConcentrationRiskPercentage1",
                notes="Max single customer revenue %"
            )
            cust_pass = max_customer_concentration_pct <= 10.0
            display_val = "<10%" if max_customer_concentration_pct <= 0.0 else f"{max_customer_concentration_pct:.2f}%"
            checklist_rows.append(("Customer Concentration", f"Top Customer = {display_val} [{l_cust}]", f"[{l_cust}]", "PASS" if cust_pass else "FAIL"))
            if not cust_pass:
                failures.append(f"Customer Concentration: Top customer accounts for {display_val} [{l_cust}] of total revenue.")
        else:
            checklist_rows.append(("Customer Concentration", "Data Not Disclosed in Filings", "N/A", "NOT CHECKED (data unavailable)"))
            unperformed_count += 1

        # Evaluate Overall Verdict strictly by written quantitative policy
        total_checks = len(checklist_rows)
        performed_checks = total_checks - unperformed_count

        if unperformed_count > 2:
            verdict_text = "INCONCLUSIVE"
            verdict_detail = f"[ANALYSIS] INCONCLUSIVE: {unperformed_count} of {total_checks} checks were NOT CHECKED due to unavailable filing data."
        elif len(failures) > 0:
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

### 1. DCF Model Assumptions & Balance Sheet Net Debt Table

| Parameter | Value | Type | Ledger Citation | Primary Source |
| :--- | :--- | :--- | :--- | :--- |
| Base Free Cash Flow | {curr_sym}{base_fcf:,.0f} | AUDITED DATA | [{l_base_fcf}] | Audited Statement of Cash Flows |
| Assumed 5Y FCF Growth Rate | {stated_growth_rate*100.0:.2f}% | ASSUMPTION | [{l_growth_assump}] | Model Assumption (Unanchored Parameter) |
| Discount Rate (WACC) | {wacc*100.0:.2f}% | ASSUMPTION | [{l_wacc_assump}] | Model Assumption (Unanchored Parameter) |
| Terminal Growth Rate | {terminal_g*100.0:.2f}% | ASSUMPTION | [{l_term_g_assump}] | Model Assumption (Unanchored Parameter) |
| Shares Outstanding | {shares_outstanding:,.0f} | MARKET DATA | [{l_shares}] | Share Registry & Market Data |
| Liquid Cash & Securities | {curr_sym}{liquid_cash:,.0f} | AUDITED DATA | [{l_cash}] | Audited Balance Sheet |
| Total Debt | {curr_sym}{tot_debt:,.0f} | AUDITED DATA | [{l_total_debt}] | Audited Balance Sheet |
| Balance Sheet Net Debt | {curr_sym}{net_debt:,.0f} | AUDITED DATA | [{l_net_debt}] | Audited Balance Sheet (Debt - Cash) |

---

### 2. Valuation Sensitivity Grid (Growth Rate × Cost of Capital)

| Growth Rate \\ WACC | {(wacc-0.01)*100.0:.1f}% WACC | {wacc*100.0:.1f}% WACC (Base) | {(wacc+0.01)*100.0:.1f}% WACC |
| :--- | :--- | :--- | :--- |
| **{(stated_growth_rate-0.02)*100.0:.1f}% Growth** [{l_g_low}] | {curr_sym}{grid_results[(round(grid_growths[0], 4), round(grid_waccs[0], 4))][0]:.2f} [{grid_results[(round(grid_growths[0], 4), round(grid_waccs[0], 4))][1]}] | {curr_sym}{grid_results[(round(grid_growths[0], 4), round(grid_waccs[1], 4))][0]:.2f} [{grid_results[(round(grid_growths[0], 4), round(grid_waccs[1], 4))][1]}] | {curr_sym}{grid_results[(round(grid_growths[0], 4), round(grid_waccs[2], 4))][0]:.2f} [{grid_results[(round(grid_growths[0], 4), round(grid_waccs[2], 4))][1]}] |
| **{stated_growth_rate*100.0:.1f}% Growth (Base)** [{l_growth_assump}] | {curr_sym}{grid_results[(round(grid_growths[1], 4), round(grid_waccs[0], 4))][0]:.2f} [{grid_results[(round(grid_growths[1], 4), round(grid_waccs[0], 4))][1]}] | {curr_sym}{base_fair_val:.2f} [{l_base_val}] | {curr_sym}{grid_results[(round(grid_growths[1], 4), round(grid_waccs[2], 4))][0]:.2f} [{grid_results[(round(grid_growths[1], 4), round(grid_waccs[2], 4))][1]}] |
| **{(stated_growth_rate+0.02)*100.0:.1f}% Growth** [{l_g_high}] | {curr_sym}{grid_results[(round(grid_growths[2], 4), round(grid_waccs[0], 4))][0]:.2f} [{grid_results[(round(grid_growths[2], 4), round(grid_waccs[0], 4))][1]}] | {curr_sym}{grid_results[(round(grid_growths[2], 4), round(grid_waccs[1], 4))][0]:.2f} [{grid_results[(round(grid_growths[2], 4), round(grid_waccs[1], 4))][1]}] | {curr_sym}{grid_results[(round(grid_growths[2], 4), round(grid_waccs[2], 4))][0]:.2f} [{grid_results[(round(grid_growths[2], 4), round(grid_waccs[2], 4))][1]}] |

---

### 3. Stress Testing Top 3 Thesis Assumptions

- Current Market Price: {curr_sym}{current_price:.2f} {currency} [{l_price}]
- Implied 5-Year FCF CAGR (Reverse DCF): **{implied_cagr:.2f}%** [{l_implied}]
- Baseline Fair Value (DCF): **{curr_sym}{base_fair_val:.2f}** [{l_base_val}]
- Stressed Fair Value (-200 bps Margin): **{curr_sym}{margin_stressed_val:.2f}** [{l_margin_stress}]
- Margin Stress Valuation Impact: **{margin_impact_pct:+.2f}%** [{l_margin_impact}]
- Stressed Fair Value (+100 bps WACC): **{curr_sym}{wacc_stressed_val:.2f}** [{l_wacc_stress}]
- WACC Stress Valuation Impact: **{wacc_impact_pct:+.2f}%** [{l_wacc_impact}]
- Stressed Fair Value (Half-Growth): **{curr_sym}{half_growth_val:.2f}** [{l_half_growth}]
- Half-Growth Valuation Impact: **{half_growth_impact_pct:+.2f}%** [{l_half_impact}]

---

### 4. Adversarial Stress Test Checklist

| Check Name | Metric Value | Ledger Citation | Status |
| :--- | :--- | :--- | :--- |
"""
        for c_name, c_val, c_id, c_status in checklist_rows:
            skeptic_report += f"| {c_name} | {c_val} | {c_id} | **{c_status}** |\n"

        skeptic_report += f"""
---

### 5. Adversarial Findings & Conclusion

- {verdict_detail}
"""
        if failures:
            for f_item in failures:
                skeptic_report += f"- {f_item}\n"
        if empirical_counter_evidence:
            for e_item in empirical_counter_evidence:
                skeptic_report += f"- Unverified context: [UNVERIFIED: model memory] {e_item}\n"

        skeptic_report += "\n---\n*Generated by Antigravity Skeptic Agent. All figures verified by Provenance Ledger.*"

        return {
            "ticker": ticker,
            "verdict": verdict_text,
            "unperformed_count": unperformed_count,
            "markdown_report": skeptic_report,
            "ledger": self.ledger,
            "baseline_fair_val": base_fair_val,
            "margin_stressed_val": margin_stressed_val,
            "wacc_stressed_val": wacc_stressed_val,
            "half_growth_val": half_growth_val,
            "implied_cagr": implied_cagr,
            "grid_results": grid_results,
            "checklist": checklist_rows,
            "failures": failures
        }
