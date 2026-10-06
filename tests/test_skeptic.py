"""
Unit tests for Skeptic Agent (/agents/skeptic.py) and adversarial review verification.
Tests both weak-thesis (vulnerable) and solid-thesis (robust) scenarios and verifies all outputs.
"""

import os
import json
import pytest
from tools.ledger import ProvenanceLedger
from agents.skeptic import SkepticAgent
from agents.verifier import ReportVerifier

def test_skeptic_weak_thesis(tmp_path):
    """Test Skeptic on an overstretched, weak thesis with empirical headwind."""
    ledger = ProvenanceLedger(run_id="skeptic_weak_test")
    skeptic = SkepticAgent(ledger=ledger)

    # Overvalued case: Price $250.0 on FCF $5.0 with 1.0 share -> Implied CAGR > 35%
    eval_res = skeptic.evaluate_thesis(
        ticker="WEAK_CO",
        current_price=250.0,
        shares_outstanding=1.0,
        base_fcf=5.0,
        base_operating_margin=0.20,
        stated_growth_rate=0.08,
        historical_3y_fcf_cagr=0.05,
        historical_5y_fcf_cagr=0.04,
        receivables_growth_yoy=0.15,
        inventory_growth_yoy=0.12,
        revenue_growth_yoy=0.05,
        short_term_debt=80.0,
        cash_and_equivalents=50.0,
        max_customer_concentration_pct=22.0,
        # Qualitative empirical evidence with NO numbers (Rule 1 compliance)
        empirical_counter_evidence=[
            "Customer churn increased significantly in recent quarters.",
            "Key accounts have delayed contract renewals."
        ]
    )

    assert eval_res["verdict"] == "VULNERABLE / STRETCHED"
    assert "Valuation Stretch" in eval_res["markdown_report"]
    assert "Working Capital Divergence" in eval_res["markdown_report"]
    assert "Customer Concentration" in eval_res["markdown_report"]

    # Save report & ledger sidecar and verify with ReportVerifier
    rep_file = tmp_path / "weak_thesis_skeptic.md"
    sidecar_file = tmp_path / "weak_thesis_skeptic.provenance.json"

    with open(rep_file, "w", encoding="utf-8") as f:
        f.write(eval_res["markdown_report"])
    eval_res["ledger"].save_sidecar(str(sidecar_file))

    verifier = ReportVerifier(report_path=str(rep_file), ledger_path=str(sidecar_file))
    audit_res = verifier.audit()

    # Skeptic report must have zero wrong figures
    assert audit_res["summary"]["total_wrong"] == 0
    assert audit_res["summary"]["status"] == "PASS WITH FLAGS"
    # Tagged model memory claims are qualitative only
    memory_claims = [u for u in audit_res["unverifiable"] if u.get("error_type") == "MODEL_MEMORY_TAGGED"]
    assert len(memory_claims) == 2

def test_skeptic_solid_thesis(tmp_path):
    """Test Skeptic on a reasonably valued, solid thesis that satisfies all hurdle thresholds."""
    ledger = ProvenanceLedger(run_id="skeptic_solid_test")
    skeptic = SkepticAgent(ledger=ledger)

    # Solid case: Price $100.0 on FCF $10.0 with 1.0 share -> Implied CAGR ~1.5% <= 7.0%
    eval_res = skeptic.evaluate_thesis(
        ticker="SOLID_CO",
        current_price=100.0,
        shares_outstanding=1.0,
        base_fcf=10.0,
        base_operating_margin=0.30,
        stated_growth_rate=0.06,
        historical_3y_fcf_cagr=0.06,
        historical_5y_fcf_cagr=0.065,
        receivables_growth_yoy=0.04,
        inventory_growth_yoy=0.03,
        revenue_growth_yoy=0.04,
        short_term_debt=10.0,
        cash_and_equivalents=100.0,
        max_customer_concentration_pct=5.0,
        net_debt=0.0,
        wacc=0.09,
        terminal_g=0.025,
        empirical_counter_evidence=None
    )

    assert eval_res["verdict"] == "ROBUST / NO STRONG COUNTER-EVIDENCE FOUND"
    assert "No strong counter-evidence found among the checks performed" in eval_res["markdown_report"]

    # Save report & ledger sidecar and verify with ReportVerifier
    rep_file = tmp_path / "solid_thesis_skeptic.md"
    sidecar_file = tmp_path / "solid_thesis_skeptic.provenance.json"

    with open(rep_file, "w", encoding="utf-8") as f:
        f.write(eval_res["markdown_report"])
    eval_res["ledger"].save_sidecar(str(sidecar_file))

    verifier = ReportVerifier(report_path=str(rep_file), ledger_path=str(sidecar_file))
    audit_res = verifier.audit()

    # Skeptic report on solid thesis has zero errors and passes 100%
    assert audit_res["summary"]["status"] == "PASS"
    assert audit_res["summary"]["total_wrong"] == 0
    assert audit_res["summary"]["total_unverifiable"] == 0

def test_skeptic_wacc_dependency():
    """Verify that every dependent output changes dynamically when WACC input changes (no cached/hard-coded values)."""
    ledger1 = ProvenanceLedger(run_id="skeptic_wacc_test_1")
    skeptic1 = SkepticAgent(ledger=ledger1)
    res_wacc_1 = skeptic1.evaluate_thesis(
        ticker="AAPL",
        current_price=250.0,
        shares_outstanding=15000000000.0,
        base_fcf=100000000000.0,
        base_operating_margin=0.30,
        stated_growth_rate=0.08,
        wacc=0.085,
        net_debt=-30000000000.0,
        terminal_g=0.025
    )

    ledger2 = ProvenanceLedger(run_id="skeptic_wacc_test_2")
    skeptic2 = SkepticAgent(ledger=ledger2)
    res_wacc_2 = skeptic2.evaluate_thesis(
        ticker="AAPL",
        current_price=250.0,
        shares_outstanding=15000000000.0,
        base_fcf=100000000000.0,
        base_operating_margin=0.30,
        stated_growth_rate=0.08,
        wacc=0.095,
        net_debt=-30000000000.0,
        terminal_g=0.025
    )

    # 1. Baseline fair value must change (higher discount rate lowers fair value)
    assert res_wacc_1["baseline_fair_val"] != res_wacc_2["baseline_fair_val"]
    assert res_wacc_1["baseline_fair_val"] > res_wacc_2["baseline_fair_val"]

    # 2. Margin-stressed fair value must change
    assert res_wacc_1["margin_stressed_val"] != res_wacc_2["margin_stressed_val"]
    assert res_wacc_1["margin_stressed_val"] > res_wacc_2["margin_stressed_val"]

    # 3. WACC-stressed fair value must change
    assert res_wacc_1["wacc_stressed_val"] != res_wacc_2["wacc_stressed_val"]
    assert res_wacc_1["wacc_stressed_val"] > res_wacc_2["wacc_stressed_val"]

    # 4. Half-growth fair value must change
    assert res_wacc_1["half_growth_val"] != res_wacc_2["half_growth_val"]
    assert res_wacc_1["half_growth_val"] > res_wacc_2["half_growth_val"]

    # 5. Implied CAGR must change (higher hurdle rate requires higher growth to justify current market price)
    assert res_wacc_1["implied_cagr"] != res_wacc_2["implied_cagr"]
    assert res_wacc_1["implied_cagr"] < res_wacc_2["implied_cagr"]

