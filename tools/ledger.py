"""
Provenance Ledger System with Cryptographic Integrity Verification
Tracks every financial data extraction and calculation with an immutable ledger ID,
source URL, input parameters, timestamp, raw output, and SHA-256 integrity signature.
"""

import re
import json
import os
import hmac
import hashlib
import datetime
import warnings
import secrets
from typing import Dict, Any, Optional, List

_SESSION_HMAC_KEY: Optional[bytes] = None
KEY_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".provenance_key.sec")
DEFAULT_HMAC_KEY = b"antigravity-finance-hmac-key-v1"

def get_hmac_key() -> bytes:
    """Load HMAC signing key from environment or persistent workspace key file, enforcing cryptographic security."""
    global _SESSION_HMAC_KEY
    key_str = os.getenv("LEDGER_HMAC_KEY")
    if key_str:
        return key_str.encode("utf-8")
    
    strict = os.getenv("LEDGER_HMAC_STRICT", "").lower() in ("1", "true", "yes")
    if strict:
        raise ValueError("LEDGER_HMAC_KEY environment variable is required in strict mode.")

    # Explicit test/legacy override mode
    if os.getenv("LEDGER_HMAC_STRICT") == "0":
        return DEFAULT_HMAC_KEY

    # Persistent workspace key ensures cross-process verifier consistency
    if os.path.exists(KEY_FILE_PATH):
        try:
            with open(KEY_FILE_PATH, "rb") as f:
                content = f.read().strip()
                if len(content) >= 32:
                    return content
        except Exception:
            pass

    # Generate and persist a cryptographic 256-bit key for this workspace
    if _SESSION_HMAC_KEY is None:
        _SESSION_HMAC_KEY = secrets.token_bytes(32)
        with open(KEY_FILE_PATH, "wb") as f:
            f.write(_SESSION_HMAC_KEY)
    return _SESSION_HMAC_KEY

def compute_entry_hash(
    ledger_id: str,
    tool: str,
    inputs: Dict[str, Any],
    raw_value: Any,
    source: str,
    timestamp: str,
    currency: Optional[str] = None,
    unit: Optional[str] = None,
    period_end: Optional[str] = None,
    fiscal_year: Optional[str] = None,
    run_id: Optional[str] = None,
    accession: Optional[str] = None,
    url: Optional[str] = None,
    notes: Optional[str] = None,
    source_tag: Optional[str] = None,
    form: Optional[str] = None
) -> str:
    """Compute true HMAC-SHA256 signature of all ledger entry fields to detect tampering."""
    serialized_inputs = json.dumps(inputs, sort_keys=True)
    payload = f"{ledger_id}|{tool}|{serialized_inputs}|{raw_value}|{source}|{timestamp}|{currency or ''}|{unit or ''}|{period_end or ''}|{fiscal_year or ''}|{run_id or ''}|{accession or ''}|{url or ''}|{notes or ''}|{source_tag or ''}|{form or ''}"
    return hmac.new(get_hmac_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()

class ProvenanceLedger:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.entries: Dict[str, Dict[str, Any]] = {}
        self._counter = 1

    def format_citation(self, ledger_id: str, run_scoped: bool = False) -> str:
        """Format a citation token, optionally scoped by the unique execution run ID."""
        if run_scoped:
            return f"[{self.run_id}:{ledger_id}]"
        return f"[{ledger_id}]"

    def record(
        self,
        tool: str,
        inputs: Dict[str, Any],
        output: Any,
        source: str,
        form: Optional[str] = None,
        period: Optional[str] = None,
        raw_value: Optional[Any] = None,
        notes: Optional[str] = None,
        ticker: Optional[str] = None,
        currency: Optional[str] = None,
        unit: Optional[str] = None,
        period_end: Optional[str] = None,
        fiscal_year: Optional[str] = None,
        source_tag: Optional[str] = None,
        accession: Optional[str] = None,
        url: Optional[str] = None
    ) -> str:
        """Record a data extraction or calculation in the provenance ledger.
        Generates a unique ledger ID and cryptographic integrity signature.
        """
        ledger_id = f"LEDGER_{self._counter:04d}"
        self._counter += 1
        
        val = raw_value if raw_value is not None else output
        ts = datetime.datetime.now().isoformat()
        
        resolved_ticker = ticker or inputs.get("ticker") or inputs.get("symbol")
        resolved_currency = currency or inputs.get("currency")
        if not resolved_currency:
            if resolved_ticker in ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"):
                resolved_currency = "USD"
            elif resolved_ticker and (resolved_ticker.endswith(".NS") or resolved_ticker.endswith(".BO")):
                resolved_currency = "INR"
            elif resolved_ticker and resolved_ticker.endswith(".L"):
                resolved_currency = "GBP"
            elif resolved_ticker and resolved_ticker.endswith(".DE"):
                resolved_currency = "EUR"
            elif resolved_ticker and (resolved_ticker.endswith(".TO") or resolved_ticker.endswith(".V")):
                resolved_currency = "CAD"
            elif inputs.get("unit") in ("USD", "INR", "EUR", "GBP"):
                resolved_currency = inputs.get("unit")
        resolved_unit = unit or inputs.get("unit") or "base"
        
        resolved_period_end = period_end or inputs.get("period_end") or inputs.get("end_date") or inputs.get("end")
        resolved_fiscal_year = fiscal_year or inputs.get("fiscal_year") or inputs.get("fy")
        if not resolved_fiscal_year and period and ("FY" in str(period) or str(period).startswith("20")):
            resolved_fiscal_year = str(period)
        if not resolved_period_end and period and re.match(r'^\d{4}-\d{2}-\d{2}$', str(period)):
            resolved_period_end = str(period)

        resolved_accession = accession or inputs.get("accession") or inputs.get("accession_number")
        resolved_url = url or inputs.get("url") or (str(source) if str(source).startswith("http") else None)
            
        resolved_source_tag = source_tag
        if not resolved_source_tag:
            src_str = str(source).lower()
            if "sec" in src_str or "edgar" in src_str:
                resolved_source_tag = "SEC"
            elif "yfinance" in src_str or "yahoo" in src_str:
                resolved_source_tag = "yfinance"
            elif "finnhub" in src_str:
                resolved_source_tag = "Finnhub"
            elif "fmp" in src_str:
                resolved_source_tag = "FMP"
            elif "cache" in src_str:
                resolved_source_tag = "cache"
            elif "calc" in tool:
                resolved_source_tag = "calc"
            else:
                resolved_source_tag = "primary_filing"

        entry_hash = compute_entry_hash(
            ledger_id=ledger_id,
            tool=tool,
            inputs=inputs,
            raw_value=val,
            source=source,
            timestamp=ts,
            currency=resolved_currency,
            unit=resolved_unit,
            period_end=resolved_period_end,
            fiscal_year=resolved_fiscal_year,
            run_id=self.run_id,
            accession=resolved_accession,
            url=resolved_url,
            notes=notes,
            source_tag=resolved_source_tag,
            form=form
        )
        
        entry = {
            "ledger_id": ledger_id,
            "run_id": self.run_id,
            "tool": tool,
            "ticker": resolved_ticker,
            "currency": resolved_currency,
            "unit": resolved_unit,
            "period_end": resolved_period_end,
            "fiscal_year": resolved_fiscal_year,
            "accession": resolved_accession,
            "url": resolved_url,
            "source_tag": resolved_source_tag,
            "inputs": inputs,
            "output": output,
            "raw_value": val,
            "source": source,
            "form": form,
            "period": period,
            "notes": notes,
            "timestamp": ts,
            "integrity_hash": entry_hash
        }
        self.entries[ledger_id] = entry
        return ledger_id

    def verify_entry_integrity(self, ledger_id: str) -> bool:
        """Verify that a ledger entry has not been modified after creation."""
        entry = self.entries.get(ledger_id)
        if not entry or "integrity_hash" not in entry:
            return False
            
        expected_hash = compute_entry_hash(
            ledger_id=entry["ledger_id"],
            tool=entry["tool"],
            inputs=entry["inputs"],
            raw_value=entry["raw_value"],
            source=entry["source"],
            timestamp=entry["timestamp"],
            currency=entry.get("currency"),
            unit=entry.get("unit"),
            period_end=entry.get("period_end"),
            fiscal_year=entry.get("fiscal_year"),
            run_id=entry.get("run_id"),
            accession=entry.get("accession"),
            url=entry.get("url"),
            notes=entry.get("notes"),
            source_tag=entry.get("source_tag"),
            form=entry.get("form")
        )
        if hmac.compare_digest(entry["integrity_hash"], expected_hash):
            return True

        strict = os.getenv("LEDGER_HMAC_STRICT", "1").lower() in ("1", "true", "yes")
        if strict:
            return False

        # Backwards compatibility check only for legacy unmigrated entries
        legacy_payload = f"{entry['ledger_id']}|{entry['tool']}|{json.dumps(entry['inputs'], sort_keys=True)}|{entry['raw_value']}|{entry['source']}|{entry['timestamp']}|{entry.get('currency') or ''}|{entry.get('unit') or ''}|{entry.get('period_end') or ''}|{entry.get('fiscal_year') or ''}"
        legacy_hash = hmac.new(get_hmac_key(), legacy_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(entry["integrity_hash"], legacy_hash)

    def get(self, ledger_id: str) -> Optional[Dict[str, Any]]:
        return self.entries.get(ledger_id)

    def get_entry(self, ledger_id: str) -> Optional[Dict[str, Any]]:
        return self.entries.get(ledger_id)

    def save_sidecar(self, filepath: str) -> str:
        """Save the provenance ledger as a sidecar JSON file next to a report."""
        sidecar_path = filepath if filepath.endswith(".provenance.json") else f"{os.path.splitext(filepath)[0]}.provenance.json"
        with open(sidecar_path, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": self.run_id,
                "saved_at": datetime.datetime.now().isoformat(),
                "total_records": len(self.entries),
                "entries": self.entries
            }, f, indent=2)
        return sidecar_path

    @classmethod
    def load_sidecar(cls, filepath: str) -> "ProvenanceLedger":
        sidecar_path = filepath if filepath.endswith(".provenance.json") else f"{os.path.splitext(filepath)[0]}.provenance.json"
        if not os.path.exists(sidecar_path):
            raise FileNotFoundError(f"Provenance sidecar not found at {sidecar_path}")
            
        with open(sidecar_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        instance = cls(run_id=data.get("run_id"))
        instance.entries = data.get("entries", {})
        if instance.entries:
            ids = [int(k.split("_")[-1]) for k in instance.entries.keys() if "_" in k and k.split("_")[-1].isdigit()]
            instance._counter = (max(ids) + 1) if ids else 1
        return instance
