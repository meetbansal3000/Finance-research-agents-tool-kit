"""
Unit tests for the Skeptic Agent (/agents/skeptic.py)
Tests:
1. Weak thesis evaluation (catches valuation stretch and downside shocks).
2. Solid thesis evaluation (states plainly "No strong counter-evidence found").
3. Full verification of both skeptic outputs via ReportVerifier.
"""

import os
import pytest
from tools.ledger import ProvenanceLedger
from agents.skeptic import SkepticAgent
from agents.verifier import ReportVerifier

def test_skeptic_weak_thesis(tmp_path):
    """Test Skeptic on an overstretched, weak thesis."""
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
        net_debt=0.0,
        wacc=0.09,
        terminal_g=0.025,
        empirical_counter_evidence=["Customer churn increased in recent quarters."]
    )
    
    assert eval_res["is_weak_thesis"] is True
    assert eval_res["implied_cagr"] > 25.0
    assert "Valuation Stretch" in eval_res["markdown_report"]
    assert "Empirical Headwind" in eval_res["markdown_report"]
    
    # Save report & ledger sidecar and verify with ReportVerifier
    rep_file = tmp_path / "weak_thesis_skeptic.md"
    sidecar_file = tmp_path / "weak_thesis_skeptic.provenance.json"
    
    with open(rep_file, "w", encoding="utf-8") as f:
        f.write(eval_res["markdown_report"])
    eval_res["ledger"].save_sidecar(str(sidecar_file))
    
    verifier = ReportVerifier(report_path=str(rep_file), ledger_path=str(sidecar_file))
    audit_res = verifier.audit()
    
    # Skeptic report must have zero value discrepancies and zero untracked figures
    assert audit_res["summary"]["total_wrong"] == 0
    # The declared model memory tag is correctly audited as MODEL_MEMORY_TAGGED under unverifiable
    assert any(u["error_type"] == "MODEL_MEMORY_TAGGED" for u in audit_res["unverifiable"])
    assert audit_res["summary"]["total_confirmed"] >= 6

def test_skeptic_solid_thesis(tmp_path):
    """Test Skeptic on a reasonably valued, solid thesis."""
    ledger = ProvenanceLedger(run_id="skeptic_solid_test")
    skeptic = SkepticAgent(ledger=ledger)
    
    # Solid case: Price $100.0 on FCF $10.0 with 1.0 share -> Implied CAGR ~1.5%
    eval_res = skeptic.evaluate_thesis(
        ticker="SOLID_CO",
        current_price=100.0,
        shares_outstanding=1.0,
        base_fcf=10.0,
        base_operating_margin=0.30,
        stated_growth_rate=0.06,
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
    assert audit_res["summary"]["total_confirmed"] >= 6
