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
        historical_fcf_cagr=0.05,
        receivables_growth_yoy=0.15,
        revenue_growth_yoy=0.05,
        empirical_counter_evidence=["Customer churn increased in recent quarters."]
    )

    assert eval_res["is_weak_thesis"] is True
    assert eval_res["implied_cagr"] > 25.0
    assert "Valuation Stretch" in eval_res["markdown_report"]
    assert "Empirical Filing Headwind" in eval_res["markdown_report"]
    assert "Working Capital Divergence" in eval_res["markdown_report"]

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
    # Tagged model memory claims are accepted as declared unverified
    memory_claims = [u for u in audit_res["unverifiable"] if u.get("error_type") == "MODEL_MEMORY_TAGGED"]
    assert len(memory_claims) == 1

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
        historical_fcf_cagr=0.06,
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

    assert eval_res["is_weak_thesis"] is False
    assert "No strong counter-evidence found." in eval_res["markdown_report"]
    assert "ROBUST / NO STRONG COUNTER-EVIDENCE FOUND" in eval_res["markdown_report"]

    # Save report & ledger sidecar and verify with ReportVerifier
    rep_file = tmp_path / "solid_thesis_skeptic.md"
    sidecar_file = tmp_path / "solid_thesis_skeptic.provenance.json"

    with open(rep_file, "w", encoding="utf-8") as f:
        f.write(eval_res["markdown_report"])
    eval_res["ledger"].save_sidecar(str(sidecar_file))

    verifier = ReportVerifier(report_path=str(rep_file), ledger_path=str(sidecar_file))
    audit_res = verifier.audit()

    # Skeptic report on solid thesis has zero errors and passes 100%
    assert audit_res["summary"]["status"] == "PASSED"
    assert audit_res["summary"]["total_wrong"] == 0
    assert audit_res["summary"]["total_unverifiable"] == 0
