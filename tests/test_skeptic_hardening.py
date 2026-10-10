"""
tests/test_skeptic_hardening.py
Unit tests verifying Skeptic institutional hardening rules:
1. Customer concentration output states method/source; <= 0% is displayed as "<10%", never 0.0%.
2. Immaterial inventory check (<2% of revenue or software/service) is NOT APPLICABLE and excluded from performed-checks count.
3. Verdict strictly follows written policy without being overridden by unverified qualitative memory claims.
"""

import pytest
from agents.skeptic import SkepticAgent
from tools.ledger import ProvenanceLedger

def test_skeptic_immaterial_inventory_and_verdict_policy():
    ledger = ProvenanceLedger(run_id="test_skeptic_rules")
    skeptic = SkepticAgent(ledger=ledger)
    
    # Run evaluation where inventory is immaterial (<2% of revenue) and all checks pass
    res = skeptic.evaluate_thesis(
        ticker="TCS.NS",
        current_price=2156.0,
        shares_outstanding=3618087518.0,
        base_fcf=449710000000.0,
        base_operating_margin=0.244,
        stated_growth_rate=0.06,
        historical_3y_fcf_cagr=0.0757,
        short_term_debt=15540000000.0,
        cash_and_equivalents=417330000000.0,
        total_debt=112830000000.0,
        max_customer_concentration_pct=0.0, # No customer > 10%
        empirical_counter_evidence=[
            "Discretionary IT spending delays in North America",
            "Wage inflation and delivery cost pressure"
        ]
    )
    
    # 1. Immaterial / Software business inventory must be NOT APPLICABLE
    inv_row = [r for r in res["checklist_rows"] if r[0] == "Inventory Divergence"][0]
    assert inv_row[3] == "NOT APPLICABLE"
    
    # 2. Customer concentration must display "<10%"
    cust_row = [r for r in res["checklist_rows"] if r[0] == "Customer Concentration"][0]
    assert "<10%" in cust_row[1]
    assert "0.0%" not in cust_row[1]
    
    # 3. Verdict must be ROBUST because 0 quantitative failures occurred (unverified memory claims do NOT flip verdict to VULNERABLE)
    assert res["verdict_text"] == "ROBUST / NO STRONG COUNTER-EVIDENCE FOUND"
    assert "VULNERABLE" not in res["verdict_text"]
    assert "ROBUST" in res["markdown_report"]

def test_nvidia_customer_concentration_detection():
    from agents.note_extractor import NoteExtractorAgent
    agent = NoteExtractorAgent()
    res = agent.extract_notes_disclosure("NVDA", "0001045810")
    
    assert res["status"] == "SUCCESS"
    assert res["has_concentration_above_10"] is True
    assert res["max_customer_concentration_pct"] >= 10.0
    assert any(c["percentage"] == 22.0 for c in res["customers"])
