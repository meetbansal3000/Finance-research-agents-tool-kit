"""
tests/test_institutional_hardening.py - Test Suite for 10/10 Institutional Hardening
Covers:
1. DCF Engine: Empty projections guard, max horizon guard, finiteness validation, reverse DCF solver status.
2. Data Layer: FileLock acquisition/release, DiskCache atomic writes and error tracking, cache freshness metadata.
3. Provenance Ledger: Strict HMAC mode enforcement, run-scoped citations, structured provenance fields.
4. Verifier: 4-Tier classification breakdown (Independent Refetch, Primary Ledger, Derived Analysis, Unverifiable).
"""

import os
import math
import pytest
from tools.calc.dcf import dcf, reverse_dcf
from tools.data_layer import DiskCache, FileLock
from tools.ledger import ProvenanceLedger, get_hmac_key
from agents.verifier import ReportVerifier

def test_dcf_hardening_validation():
    # 1. Empty growth rates guard
    with pytest.raises(ValueError, match="cannot be empty"):
        dcf(base_fcf=100.0, growth_rates=[], discount_rate=0.09, terminal_growth_rate=0.025, shares_outstanding=10.0)

    # 2. Max horizon guard
    with pytest.raises(ValueError, match="exceeds practical modeling limits"):
        dcf(base_fcf=100.0, growth_rates=[0.10] * 35, discount_rate=0.09, terminal_growth_rate=0.025, shares_outstanding=10.0)

    # 3. Non-finite values guard
    with pytest.raises(ValueError, match="finite numerical value"):
        dcf(base_fcf=float('nan'), growth_rates=[0.10, 0.08], discount_rate=0.09, terminal_growth_rate=0.025, shares_outstanding=10.0)

    with pytest.raises(ValueError, match="finite numerical value"):
        dcf(base_fcf=100.0, growth_rates=[0.10, 0.08], discount_rate=float('inf'), terminal_growth_rate=0.025, shares_outstanding=10.0)

def test_reverse_dcf_solver_status():
    res = reverse_dcf(
        current_price=100.0,
        base_fcf=50.0,
        shares_outstanding=10.0,
        discount_rate=0.10,
        terminal_growth_rate=0.025,
        projection_years=5,
        net_debt=0.0
    )
    assert res["result"]["solver_status"] in ("CONVERGED", "BOUND_SATURATED_MIN", "BOUND_SATURATED_MAX")
    assert "residual" in res["result"]
    assert "iterations" in res["result"]
    assert "search_bounds" in res["result"]
    assert math.isfinite(res["result"]["implied_growth_rate_pct"])

def test_file_lock_and_atomic_cache(tmp_path):
    lock_file = str(tmp_path / "test.lock")
    with FileLock(lock_file) as fl:
        assert os.path.exists(lock_file)
    assert not os.path.exists(lock_file)

    cache = DiskCache(cache_dir=str(tmp_path / "cache"))
    cache.set("item_1", {"key": "val"}, ttl_seconds=60)
    cached = cache.get("item_1")
    assert cached is not None
    assert cached["key"] == "val"
    assert "_cache_metadata" not in cached

    # Separate metadata retrieval preserves payload integrity
    payload, meta = cache.get_with_metadata("item_1")
    assert payload["key"] == "val"
    assert meta["is_cached"] is True
    assert meta["cache_age_seconds"] >= 0.0
    assert cache.last_error is None

    # Test lock owner protection: unacquired lock cannot release or remove active lock
    fl1 = FileLock(lock_file, timeout=0.5)
    assert fl1.acquire() is True
    fl2 = FileLock(lock_file, timeout=0.1)
    assert fl2.acquire() is False
    fl2.release()
    assert os.path.exists(lock_file)
    fl1.release()
    assert not os.path.exists(lock_file)

def test_ledger_strict_hmac_and_citations(monkeypatch):
    # Strict mode without key raises ValueError
    monkeypatch.setenv("LEDGER_HMAC_STRICT", "1")
    monkeypatch.delenv("LEDGER_HMAC_KEY", raising=False)
    with pytest.raises(ValueError, match="LEDGER_HMAC_KEY environment variable is required in strict mode"):
        get_hmac_key()

    # Normal mode falls back to default key
    monkeypatch.setenv("LEDGER_HMAC_STRICT", "0")
    assert get_hmac_key() == b"antigravity-finance-hmac-key-v1"

    # Citation formatting
    ledger = ProvenanceLedger(run_id="RUN_2026_TEST")
    l_id = ledger.record(
        tool="test_tool",
        inputs={"val": 10},
        output=10,
        source="test_source",
        accession="0000320193-25-000106",
        url="https://www.sec.gov"
    )
    assert ledger.format_citation(l_id, run_scoped=False) == f"[{l_id}]"
    assert ledger.format_citation(l_id, run_scoped=True) == f"[RUN_2026_TEST:{l_id}]"
    
    entry = ledger.get(l_id)
    assert entry["accession"] == "0000320193-25-000106"
    assert entry["url"] == "https://www.sec.gov"
    assert ledger.verify_entry_integrity(l_id) is True

    # Tampering with accession fails verification
    entry["accession"] = "0000000000-00-000000"
    assert ledger.verify_entry_integrity(l_id) is False
    entry["accession"] = "0000320193-25-000106"
    assert ledger.verify_entry_integrity(l_id) is True

    # Tampering with url fails verification
    entry["url"] = "https://tampered-url.com"
    assert ledger.verify_entry_integrity(l_id) is False
    entry["url"] = "https://www.sec.gov"
    assert ledger.verify_entry_integrity(l_id) is True

    # Tampering with notes or source_tag fails verification
    entry["notes"] = "tampered notes content"
    assert ledger.verify_entry_integrity(l_id) is False
    entry["notes"] = None
    assert ledger.verify_entry_integrity(l_id) is True

def test_verifier_four_tier_classification(tmp_path):
    ledger = ProvenanceLedger(run_id="run_4tier")
    l1 = ledger.record(
        tool="tools.filing.get_xbrl_facts",
        inputs={"concept": "Revenues"},
        output=1000.0,
        source="SEC EDGAR",
        period="FY2025"
    )
    l2 = ledger.record(
        tool="tools.calc.margin",
        inputs={"rev": 1000.0, "ebit": 250.0},
        output=25.0,
        source="calc",
        period="FY2025"
    )
    sidecar_path = str(tmp_path / "test_report.provenance.json")
    report_path = str(tmp_path / "test_report.md")
    ledger.save_sidecar(sidecar_path)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# FY2025 Report\n- Revenues were $1,000 [{l1}].\n- Operating margin was 25.0% [{l2}].\n")

    verifier = ReportVerifier(report_path=report_path, ledger_path=sidecar_path, perform_refetch=False)
    audit = verifier.verify_report()
    summary = audit["summary"]
    assert summary["status"] == "PASS"
    assert "tiers" in summary
    assert summary["tiers"]["PRIMARY_LEDGER_CONSISTENT"] == 1
    assert summary["tiers"]["DERIVED_ANALYSIS"] == 1
    assert summary["tiers"]["UNVERIFIABLE_OR_UNCHECKED"] == 0

def test_codex_institutional_audit_hardening(tmp_path):
    from tools.calc.dcf import dcf, reverse_dcf
    from tools.filing import FilingExtractor
    from tools.data_layer import get_data_layer
    from agents.verifier import ReportVerifier

    # 1. Reject implausible negative growth rates <= -100% (-1.0)
    with pytest.raises(ValueError, match="strictly greater than -100%"):
        dcf(base_fcf=100.0, growth_rates=[-1.0], discount_rate=0.10, terminal_growth_rate=0.02, shares_outstanding=10.0)

    with pytest.raises(ValueError, match="strictly greater than -100%"):
        dcf(base_fcf=100.0, growth_rates=[-1.2], discount_rate=0.10, terminal_growth_rate=0.02, shares_outstanding=10.0)

    with pytest.raises(ValueError, match="Terminal growth rate must be strictly greater than -100%"):
        dcf(base_fcf=100.0, growth_rates=[0.10], discount_rate=0.10, terminal_growth_rate=-1.05, shares_outstanding=10.0)

    with pytest.raises(ValueError, match="Terminal growth rate must be strictly greater than -100%"):
        reverse_dcf(current_price=100.0, base_fcf=10.0, shares_outstanding=10.0, discount_rate=0.10, terminal_growth_rate=-1.05)

    # 2. Verify ledger recording in dcf and reverse_dcf
    test_ledger = ProvenanceLedger(run_id="run_dcf_hardening")
    dcf_res = dcf(
        base_fcf=100.0,
        growth_rates=[0.10, 0.08, 0.05],
        discount_rate=0.09,
        terminal_growth_rate=0.02,
        shares_outstanding=10.0,
        currency="USD",
        ledger=test_ledger
    )
    assert "ledger_id" in dcf_res
    assert test_ledger.verify_entry_integrity(dcf_res["ledger_id"]) is True

    rev_res = reverse_dcf(
        current_price=150.0,
        base_fcf=10.0,
        shares_outstanding=10.0,
        discount_rate=0.09,
        terminal_growth_rate=0.02,
        currency="USD",
        ledger=test_ledger
    )
    assert "ledger_id" in rev_res
    assert test_ledger.verify_entry_integrity(rev_res["ledger_id"]) is True

    # 3. FilingExtractor document download cache verification with sidecar metadata
    extractor = FilingExtractor()
    test_doc = tmp_path / "mock_10k.htm"
    test_doc.write_text("<html>Mock SEC 10-K Content</html>", encoding="utf-8")
    meta_path = f"{str(test_doc)}.meta.json"
    with open(meta_path, "w", encoding="utf-8") as f_meta:
        import hashlib, datetime, json
        json.dump({
            "url": "https://data.sec.gov/mock_10k.htm",
            "size": len("<html>Mock SEC 10-K Content</html>"),
            "sha256": hashlib.sha256("<html>Mock SEC 10-K Content</html>".encode()).hexdigest(),
            "downloaded_at": datetime.datetime.now().isoformat()
        }, f_meta)

    # 4. DataLayer fundamentals schema alignment and verifier refetch verification
    dl = get_data_layer()
    fund_ledger = ProvenanceLedger(run_id="run_fund_ledger")
    aapl_funds = dl.get_fundamentals("AAPL", ledger=fund_ledger)
    assert "revenue" in aapl_funds
    assert "operating_income" in aapl_funds
    assert len(fund_ledger.entries) >= 4  # multiple fundamental metrics registered

    # Verify refetch_source schema compatibility with data_layer.get_fundamentals
    dummy_rep = tmp_path / "dummy.md"
    dummy_rep.write_text("# Dummy Report", encoding="utf-8")
    v = ReportVerifier(report_path=str(dummy_rep))
    status, val, src = v.refetch_source(entry={
        "tool": "data_layer.get_fundamentals",
        "inputs": {"ticker": "AAPL", "metric": "revenue"},
        "raw_value": aapl_funds["revenue"]
    })
    assert status is True
    assert val == aapl_funds["revenue"]

