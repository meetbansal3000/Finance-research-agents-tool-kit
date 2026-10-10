"""
tests/test_independent_verification.py
Verifies that:
1. The Verifier executes an independent code path from the Analyst (using SEC companyconcept API / direct iXBRL document parsing instead of analyst's companyfacts).
2. Planting a corrupted value in an analyst-extracted figure is caught as a live mismatch / verification failure.
3. Every figure that cannot be independently re-fetched is explicitly cataloged as NOT RE-FETCHED.
"""

import pytest
import tempfile
import os
from agents.verifier import ReportVerifier

def test_independent_verification_catches_planted_analyst_bug():
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as tf:
        tf.write("# Research Report AAPL\nPeriod End: 2025-09-27\nFiscal Year: FY2025\n")
        report_path = tf.name
        
    try:
        verifier = ReportVerifier(report_path=report_path, perform_refetch=True)
        
        # FY2025 Revenue is ~$416,161M (or $391,035M depending on concept)
        # Plant an obviously corrupted figure: $999,999,000,000.0 ($1 Trillion)
        planted_corrupted_revenue = 999999000000.0
        
        # Mock an analyst ledger entry with the planted bug
        mock_entry = {
            "id": "mock_entry_001",
            "tool": "edgar.get_facts",
            "inputs": {"ticker": "AAPL", "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "form": "10-K", "period_end": "2025-09-27"},
            "raw_value": planted_corrupted_revenue,
            "period_end": "2025-09-27",
            "fiscal_year": 2025,
            "currency": "USD",
            "unit": "USD",
            "source": "SEC EDGAR Form 10-K"
        }
        
        # Run verifier's independent re-fetch
        passes, live_val, source_info = verifier.refetch_source(mock_entry)
        
        # The verifier independently queried the SEC companyconcept endpoint
        # It must detect that live_val does NOT equal expected_val ($999B)
        assert passes is False
        assert live_val is not None
        assert abs(live_val - planted_corrupted_revenue) > 1e11
        assert "SEC companyconcept API" in source_info or "Primary Filing Document" in source_info
    finally:
        if os.path.exists(report_path):
            os.remove(report_path)

def test_unsupported_tool_marked_not_refetched():
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as tf:
        tf.write("# Research Report AAPL\nPeriod End: 2025-09-27\n")
        report_path = tf.name
        
    try:
        verifier = ReportVerifier(report_path=report_path, perform_refetch=True)
        
        mock_unsupported_entry = {
            "id": "mock_entry_unsupported",
            "tool": "custom_proprietary_feed.fetch_sentiment",
            "inputs": {"ticker": "AAPL"},
            "raw_value": 0.85,
            "source": "Proprietary News Sentiment"
        }
        
        passes, live_val, source_info = verifier.refetch_source(mock_unsupported_entry)
        assert passes is False
        assert live_val is None
        assert "not configured for tool" in source_info or "not supported" in source_info.lower()
    finally:
        if os.path.exists(report_path):
            os.remove(report_path)
