"""
Live SEC XBRL Re-fetch Verification Test
Pulls Apple's FY2025 Revenue, Operating Income, and Net Income directly from SEC EDGAR XBRL facts.
Filters facts by form type ('10-K') and exact period end date ('2025-09-27').
Runs the ReportVerifier to independently re-fetch and audit each claim.
"""

import os
import pytest
import urllib.request
import json
from tools.ledger import ProvenanceLedger
from agents.verifier import ReportVerifier

@pytest.mark.live
def test_live_sec_xbrl_refetch_apple_fy2025(tmp_path):
    # 1. Fetch Apple FY2025 facts directly from SEC EDGAR
    cik = "0000320193"
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    user_agent = os.getenv("SEC_EDGAR_USER_AGENT", "ResearchAnalyst research@example.com")
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        facts_data = json.loads(resp.read().decode("utf-8"))
        
    us_gaap = facts_data["facts"]["us-gaap"]
    
    # Helper to select fact by form type and period end date
    def get_fact_by_end_date(concept_name: str, form_type: str = "10-K", end_date: str = "2025-09-27"):
        units = us_gaap[concept_name]["units"]["USD"]
        matches = [u for u in units if u.get("form") == form_type and u.get("end") == end_date]
        assert len(matches) > 0, f"No matching fact for {concept_name} with form {form_type} and end {end_date}"
        return matches[-1]

    # Extract 3 facts by form type and end date
    rev_fact = get_fact_by_end_date("RevenueFromContractWithCustomerExcludingAssessedTax", "10-K", "2025-09-27")
    op_inc_fact = get_fact_by_end_date("OperatingIncomeLoss", "10-K", "2025-09-27")
    net_inc_fact = get_fact_by_end_date("NetIncomeLoss", "10-K", "2025-09-27")

    print("\n--- Selected SEC XBRL Records ---")
    print(f"Revenue: Val=${rev_fact['val']:,} | Form={rev_fact['form']} | End={rev_fact['end']} | Accn={rev_fact['accn']} | Filed={rev_fact['filed']}")
    print(f"Operating Income: Val=${op_inc_fact['val']:,} | Form={op_inc_fact['form']} | End={op_inc_fact['end']} | Accn={op_inc_fact['accn']} | Filed={op_inc_fact['filed']}")
    print(f"Net Income: Val=${net_inc_fact['val']:,} | Form={net_inc_fact['form']} | End={net_inc_fact['end']} | Accn={net_inc_fact['accn']} | Filed={net_inc_fact['filed']}")

    # 2. Record in Provenance Ledger
    ledger = ProvenanceLedger(run_id="live_aapl_test")
    
    l_rev = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        inputs={"ticker": "AAPL", "concept": "us-gaap:Revenues", "period": "FY2025", "period_end": "2025-09-27", "form": "10-K"},
        output=float(rev_fact["val"]),
        raw_value=float(rev_fact["val"]),
        source=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json (Accn: {rev_fact['accn']})",
        period="FY2025",
        form="10-K"
    )

    l_op = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        inputs={"ticker": "AAPL", "concept": "us-gaap:OperatingIncome", "period": "FY2025", "period_end": "2025-09-27", "form": "10-K"},
        output=float(op_inc_fact["val"]),
        raw_value=float(op_inc_fact["val"]),
        source=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json (Accn: {op_inc_fact['accn']})",
        period="FY2025",
        form="10-K"
    )

    l_net = ledger.record(
        tool="edgar.get_facts",
        ticker="AAPL",
        inputs={"ticker": "AAPL", "concept": "us-gaap:NetIncome", "period": "FY2025", "period_end": "2025-09-27", "form": "10-K"},
        output=float(net_inc_fact["val"]),
        raw_value=float(net_inc_fact["val"]),
        source=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json (Accn: {net_inc_fact['accn']})",
        period="FY2025",
        form="10-K"
    )

    report_file = tmp_path / "aapl_live_report.md"
    ledger_file = tmp_path / "aapl_live_report.provenance.json"
    ledger.save_sidecar(str(ledger_file))

    report_text = f"""# Apple FY2025 Audited Filing Metrics

- Apple delivered FY2025 total revenue of $416.2B [{l_rev}].
- Operating income reached $133.05B [{l_op}].
- Net income for the fiscal year ended September 27, 2025 was $112.01B [{l_net}].
"""
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    # 3. Run verifier with perform_refetch=True
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(ledger_file), perform_refetch=True)
    audit = verifier.audit()

    assert audit["summary"]["status"] == "PASSED"
    assert audit["summary"]["total_confirmed"] == 3
    assert audit["summary"]["total_wrong"] == 0
    assert audit["summary"]["total_unverifiable"] == 0
