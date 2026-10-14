"""
tests/test_document_sidecar_verifier.py
Verifies that:
1. The verifier checks that any filing document backing a ledger entry has a .meta.json sidecar.
2. If a document has no .meta.json sidecar, the audit marks it as MISSING_DOCUMENT_SIDECAR and status FAIL.
3. If the document's SHA-256 does not match the sidecar, it marks DOCUMENT_HASH_MISMATCH and status FAIL.
4. If a valid .meta.json sidecar with matching SHA-256 is present, it passes the document integrity check.
"""

import os
import json
import hashlib
import tempfile
import pytest
from tools.ledger import ProvenanceLedger
from agents.verifier import ReportVerifier

def test_missing_document_sidecar_fails(tmp_path):
    filings_dir = tmp_path / "library" / "filings"
    filings_dir.mkdir(parents=True)
    
    # Hand-written / fake document without sidecar
    fake_doc = filings_dir / "FAKE_10K.md"
    fake_doc.write_text("# Hand-written fake filing\nRevenue was $100M", encoding="utf-8")
    
    ledger = ProvenanceLedger(run_id="test_sidecar_check")
    l_id = ledger.record(
        tool="tools.filing.extract_metric",
        inputs={"ticker": "FAKE", "metric": "Revenue", "doc_path": str(fake_doc)},
        output=100000000.0,
        source=f"library/filings/FAKE_10K.md (Page 1)",
        ticker="FAKE",
        currency="USD",
        raw_value=100000000.0,
        period="FY2025",
        doc_path=str(fake_doc)
    )
    
    report_file = tmp_path / "fake_report.md"
    report_file.write_text(f"# Fake Report\nRevenue was $100M [{l_id}].", encoding="utf-8")
    sidecar_file = tmp_path / "fake_report.provenance.json"
    ledger.save_sidecar(str(sidecar_file))
    
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(sidecar_file))
    audit_res = verifier.audit()
    
    assert audit_res["summary"]["status"] == "FAIL"
    sidecar_errors = [w for w in audit_res["wrong"] if w.get("error_type") == "MISSING_DOCUMENT_SIDECAR"]
    assert len(sidecar_errors) >= 1
    assert "has no .meta.json sidecar" in sidecar_errors[0]["failure_reason"]

def test_tampered_document_hash_fails(tmp_path):
    filings_dir = tmp_path / "library" / "filings"
    filings_dir.mkdir(parents=True)
    
    doc = filings_dir / "DOWNLOADED_10K.htm"
    content = "<html>Original Content</html>"
    doc.write_text(content, encoding="utf-8")
    
    # Sidecar with hash of original content
    meta_path = str(doc) + ".meta.json"
    meta_data = {
        "url": "https://sec.gov/doc.htm",
        "http_status": 200,
        "size": len(content),
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "downloaded_at": "2026-10-12T00:00:00Z"
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f)
        
    # Tamper with the document behind the downloader's back
    doc.write_text("<html>Tampered Hand-Edited Content</html>", encoding="utf-8")
    
    ledger = ProvenanceLedger(run_id="test_tampered_doc")
    l_id = ledger.record(
        tool="tools.filing.extract_metric",
        inputs={"ticker": "TEST", "metric": "Revenue", "doc_path": str(doc)},
        output=500.0,
        source=f"library/filings/DOWNLOADED_10K.htm (Page 1)",
        ticker="TEST",
        currency="USD",
        raw_value=500.0,
        period="FY2025",
        doc_path=str(doc)
    )
    
    report_file = tmp_path / "test_report.md"
    report_file.write_text(f"# Test Report\nRevenue was $500 [{l_id}].", encoding="utf-8")
    sidecar_file = tmp_path / "test_report.provenance.json"
    ledger.save_sidecar(str(sidecar_file))
    
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(sidecar_file))
    audit_res = verifier.audit()
    
    assert audit_res["summary"]["status"] == "FAIL"
    hash_errors = [w for w in audit_res["wrong"] if w.get("error_type") == "DOCUMENT_HASH_MISMATCH"]
    assert len(hash_errors) >= 1
    assert "does not match sidecar metadata" in hash_errors[0]["failure_reason"]


def test_non_200_http_status_fails(tmp_path):
    filings_dir = tmp_path / "library" / "filings"
    filings_dir.mkdir(parents=True)
    
    doc = filings_dir / "DOWNLOADED_10K.htm"
    content = "<html>Original Content</html>"
    doc.write_text(content, encoding="utf-8")
    
    # Sidecar with HTTP 403 status
    meta_path = str(doc) + ".meta.json"
    meta_data = {
        "url": "https://www.sec.gov/doc.htm",
        "http_status": 403,
        "size": len(content),
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "downloaded_at": "2026-10-12T00:00:00Z"
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f)
        
    ledger = ProvenanceLedger(run_id="test_http_status")
    l_id = ledger.record(
        tool="tools.filing.extract_metric",
        inputs={"ticker": "TEST", "metric": "Revenue", "doc_path": str(doc)},
        output=500.0,
        source=f"library/filings/DOWNLOADED_10K.htm (Page 1)",
        ticker="TEST",
        currency="USD",
        raw_value=500.0,
        period="FY2025",
        doc_path=str(doc)
    )
    
    report_file = tmp_path / "test_report.md"
    report_file.write_text(f"# Test Report\nRevenue was $500 [{l_id}].", encoding="utf-8")
    sidecar_file = tmp_path / "test_report.provenance.json"
    ledger.save_sidecar(str(sidecar_file))
    
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(sidecar_file))
    audit_res = verifier.audit()
    
    assert audit_res["summary"]["status"] == "FAIL"
    status_errors = [w for w in audit_res["wrong"] if w.get("error_type") == "DOCUMENT_HTTP_STATUS_INVALID"]
    assert len(status_errors) >= 1
    assert "invalid HTTP status 403" in status_errors[0]["failure_reason"]


def test_unauthorized_domain_fails(tmp_path):
    filings_dir = tmp_path / "library" / "filings"
    filings_dir.mkdir(parents=True)
    
    doc = filings_dir / "DOWNLOADED_10K.htm"
    content = "<html>Original Content</html>"
    doc.write_text(content, encoding="utf-8")
    
    # Sidecar with unapproved domain
    meta_path = str(doc) + ".meta.json"
    meta_data = {
        "url": "https://malicious-site.com/fake_filing.htm",
        "http_status": 200,
        "size": len(content),
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "downloaded_at": "2026-10-12T00:00:00Z"
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f)
        
    ledger = ProvenanceLedger(run_id="test_unauth_domain")
    l_id = ledger.record(
        tool="tools.filing.extract_metric",
        inputs={"ticker": "TEST", "metric": "Revenue", "doc_path": str(doc)},
        output=500.0,
        source=f"library/filings/DOWNLOADED_10K.htm (Page 1)",
        ticker="TEST",
        currency="USD",
        raw_value=500.0,
        period="FY2025",
        doc_path=str(doc)
    )
    
    report_file = tmp_path / "test_report.md"
    report_file.write_text(f"# Test Report\nRevenue was $500 [{l_id}].", encoding="utf-8")
    sidecar_file = tmp_path / "test_report.provenance.json"
    ledger.save_sidecar(str(sidecar_file))
    
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(sidecar_file))
    audit_res = verifier.audit()
    
    assert audit_res["summary"]["status"] == "FAIL"
    domain_errors = [w for w in audit_res["wrong"] if w.get("error_type") == "DOCUMENT_DOMAIN_UNAUTHORIZED"]
    assert len(domain_errors) >= 1
    assert "not on an allowlisted domain" in domain_errors[0]["failure_reason"]


def test_source_naming_missing_file_fails(tmp_path):
    """A ledger entry whose source names a nonexistent filing document must fail with MISSING_DOCUMENT_FILE."""
    ledger = ProvenanceLedger(run_id="test_missing_doc_source")
    l_id = ledger.record(
        tool="tools.filing.extract_metric",
        inputs={"ticker": "TEST", "metric": "Revenue"},
        output=500.0,
        source="library/filings/NONEXISTENT_10K.htm (Page 1)",
        ticker="TEST",
        currency="USD",
        raw_value=500.0,
        period="FY2025"
    )
    
    report_file = tmp_path / "test_report.md"
    report_file.write_text(f"# Test Report\nRevenue was $500 [{l_id}].", encoding="utf-8")
    sidecar_file = tmp_path / "test_report.provenance.json"
    ledger.save_sidecar(str(sidecar_file))
    
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(sidecar_file), perform_refetch=False)
    audit_res = verifier.audit()
    
    assert audit_res["summary"]["status"] == "FAIL"
    missing_errors = [w for w in audit_res["wrong"] if w.get("error_type") == "MISSING_DOCUMENT_FILE"]
    assert len(missing_errors) >= 1
    assert "does not exist on disk" in missing_errors[0]["failure_reason"]


def test_doc_path_naming_missing_file_fails(tmp_path):
    """A ledger entry whose doc_path points to a missing file must fail with MISSING_DOCUMENT_FILE."""
    missing_path = tmp_path / "library" / "filings" / "MISSING_REPORT.pdf"
    ledger = ProvenanceLedger(run_id="test_missing_doc_path")
    l_id = ledger.record(
        tool="tools.filing.extract_metric",
        inputs={"ticker": "TEST", "metric": "Revenue", "doc_path": str(missing_path)},
        output=500.0,
        source="Annual Report filing",
        ticker="TEST",
        currency="USD",
        raw_value=500.0,
        period="FY2025",
        doc_path=str(missing_path)
    )
    
    report_file = tmp_path / "test_report.md"
    report_file.write_text(f"# Test Report\nRevenue was $500 [{l_id}].", encoding="utf-8")
    sidecar_file = tmp_path / "test_report.provenance.json"
    ledger.save_sidecar(str(sidecar_file))
    
    verifier = ReportVerifier(report_path=str(report_file), ledger_path=str(sidecar_file), perform_refetch=False)
    audit_res = verifier.audit()
    
    assert audit_res["summary"]["status"] == "FAIL"
    missing_errors = [w for w in audit_res["wrong"] if w.get("error_type") == "MISSING_DOCUMENT_FILE"]
    assert len(missing_errors) >= 1
    assert "does not exist on disk" in missing_errors[0]["failure_reason"]


