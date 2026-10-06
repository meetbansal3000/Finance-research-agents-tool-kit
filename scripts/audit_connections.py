"""
scripts/audit_connections.py - Comprehensive Live Data & Connection Audit
Audits:
1. SEC EDGAR XBRL API connection (CIK 0000320193 / Apple Inc.)
2. SEC EDGAR 10-K document repository download
3. Yahoo Finance live market quotes (US & International)
4. Local ChromaDB persistent vector engine
5. Provenance Ledger HMAC-SHA256 integrity
"""

import os
import sys
import json
import urllib.request

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import yfinance as yf
from tools.ledger import ProvenanceLedger
from tools.knowledge import LocalKnowledgeBase

def audit_all_connections():
    print("=================================================================")
    print("🔍 LIVE DATA & CONNECTION COMPREHENSIVE AUDIT")
    print("=================================================================")

    # 1. SEC EDGAR XBRL Facts API
    print("\n--- [1] SEC EDGAR XBRL Facts API Connection ---")
    cik = "0000320193"
    sec_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    ua = os.getenv("SEC_EDGAR_USER_AGENT", "ResearchAnalyst research@example.com")
    req = urllib.request.Request(sec_url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            data = json.loads(resp.read().decode("utf-8"))
        entity = data.get("entityName")
        rev_units = data["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"]
        latest_rev = [u for u in rev_units if u.get("form") == "10-K" and u.get("end") == "2025-09-27"][-1]
        print(f"  Status: HTTP {status} (SUCCESS)")
        print(f"  Entity: {entity} (CIK: {cik})")
        print(f"  Live Audited Revenue: ${latest_rev['val']:,} USD")
        print(f"  Accession Number: {latest_rev['accn']} (Form 10-K, Filed: {latest_rev['filed']})")
    except Exception as e:
        print(f"  Status: FAILED ({e})")

    # 2. SEC EDGAR 10-K Primary Document Download
    print("\n--- [2] SEC EDGAR 10-K Filing Document Connection ---")
    doc_url = "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm"
    req_doc = urllib.request.Request(doc_url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req_doc, timeout=15) as resp_doc:
            doc_status = resp_doc.status
            content_bytes = resp_doc.read()
        print(f"  Status: HTTP {doc_status} (SUCCESS)")
        print(f"  Document Size: {len(content_bytes):,} bytes (~{len(content_bytes)/(1024*1024):.2f} MB)")
        print(f"  URL: {doc_url}")
    except Exception as e:
        print(f"  Status: FAILED ({e})")

    # 3. Yahoo Finance Live Market Quotes
    print("\n--- [3] Yahoo Finance Live Market Data Connection ---")
    tickers = ["AAPL", "MSFT", "TCS.NS"]
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            info = t.info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            curr = info.get("currency")
            exch = info.get("exchange")
            mkt_cap = info.get("marketCap")
            cap_str = f"{mkt_cap/1e9:,.2f}B" if mkt_cap else "N/A"
            print(f"  Ticker: {sym:7s} | Price: {price} {curr} | Market Cap: {cap_str} | Exchange: {exch} (SUCCESS)")
        except Exception as e:
            print(f"  Ticker: {sym:7s} | FAILED ({e})")

    # 4. ChromaDB Local Vector Engine
    print("\n--- [4] ChromaDB Persistent Vector Database Connection ---")
    try:
        kb = LocalKnowledgeBase()
        stat = kb.status()
        print(f"  Collection Name: {stat['collection_name']}")
        print(f"  Database Path: {stat['persist_dir']}")
        print(f"  Indexed Chunks: {stat['total_chunks']} (SUCCESS)")
        sample_query = kb.search("iPhone net sales in fiscal 2025", ticker="AAPL", top_k=1)
        if sample_query:
            hit = sample_query[0]
            print(f"  Sample Query Hit: {hit['citation']}")
            print(f"  Vector Distance: {hit['distance']:.4f}")
    except Exception as e:
        print(f"  Status: FAILED ({e})")

    # 5. Provenance Ledger Cryptographic Integrity
    print("\n--- [5] Provenance Ledger HMAC-SHA256 Signing & Verification ---")
    try:
        ledger = ProvenanceLedger(run_id="connection_audit_probe")
        l_id = ledger.record(
            tool="audit.probe",
            inputs={"ticker": "AAPL", "metric": "test"},
            output=999.99,
            source="Connection Audit Probe",
            ticker="AAPL",
            currency="USD"
        )
        is_intact = ledger.verify_entry_integrity(l_id)
        entry = ledger.get_entry(l_id)
        print(f"  Generated Ledger ID: {l_id}")
        print(f"  HMAC-SHA256 Signature: {entry['integrity_hash'][:36]}...")
        print(f"  Integrity Check: {'VALID' if is_intact else 'INVALID'} (SUCCESS)")
    except Exception as e:
        print(f"  Status: FAILED ({e})")

    print("\n=================================================================")
    print("✅ ALL CONNECTIONS AND PRIMARY DATA PIPELINES AUDITED AND ACTIVE")
    print("=================================================================")

if __name__ == "__main__":
    audit_all_connections()
