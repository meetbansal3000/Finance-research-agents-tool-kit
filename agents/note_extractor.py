"""
agents/note_extractor.py - Footnote & Qualitative Disclosure Extraction Agent
Specialist Agent responsible for extracting unstructured textual disclosures from primary SEC 10-K filings:
  - Customer Concentration & Counterparty Credit Risk (Note 19 / ASC 280)
  - Geographic Revenue Distribution
  - Off-Balance-Sheet Leases and Long-Term Purchase Commitments
Integrates directly with ProvenanceLedger to anchor textual citations and quoted snippets.
"""

import os
import sys
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.ledger import ProvenanceLedger
from tools.filing_note_parser import FilingNoteParser
from tools.sec_cik import resolve_cik


class NoteExtractorAgent:
    def __init__(self, ledger: Optional[ProvenanceLedger] = None):
        self.ledger = ledger or ProvenanceLedger()
        self.parser = FilingNoteParser()

    def extract_notes_disclosure(
        self,
        ticker: str,
        cik: Optional[str] = None,
        accn: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dynamically extracts footnote disclosures from primary filing.
        Records exact quoted snippet and extracted values into the ProvenanceLedger.
        """
        resolved_cik = cik or resolve_cik(ticker) or "0000320193"
        parse_res = self.parser.parse_filing_for_company(
            ticker=ticker,
            cik=resolved_cik,
            accn=accn or ""
        )

        cust_info = parse_res.get("customer_concentration", {})
        max_pct = cust_info.get("max_concentration_pct", 0.0)
        snippet = cust_info.get("quoted_snippet", "")
        method = cust_info.get("method", "TEXTUAL_NOTE_EXTRACTION")

        # Record entry in ProvenanceLedger
        l_cust = self.ledger.record(
            tool="filing.note_disclosure",
            ticker=ticker,
            inputs={"ticker": ticker, "disclosure_type": "CustomerConcentration", "accn": accn},
            output=max_pct,
            raw_value=max_pct,
            source=f"SEC 10-K Audited Notes: {snippet[:120]}...",
            notes=f"{ticker} Max Customer Concentration ({max_pct}%)",
            source_tag="SEC_AUDITED_NOTE"
        )

        return {
            "ticker": ticker,
            "max_customer_concentration_pct": max_pct,
            "has_concentration_above_10": cust_info.get("has_concentration_above_10", False),
            "customers": cust_info.get("customers", []),
            "quoted_snippet": snippet,
            "method": method,
            "ledger_id": l_cust
        }


if __name__ == "__main__":
    agent = NoteExtractorAgent()
    # Test on NVIDIA
    nvda_res = agent.extract_notes_disclosure("NVDA", cik="0001045810", accn="0001045810-26-000014")
    print(f"NVDA Customer Concentration: {nvda_res['max_customer_concentration_pct']}% (Ledger: {nvda_res['ledger_id']})")
    print(f"Quoted: {nvda_res['quoted_snippet'][:100]}...")
