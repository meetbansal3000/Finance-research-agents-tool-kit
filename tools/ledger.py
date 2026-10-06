"""
Provenance Ledger System with Cryptographic Integrity Verification
Tracks every financial data extraction and calculation with an immutable ledger ID,
source URL, input parameters, timestamp, raw output, and SHA-256 integrity signature.
"""

import json
import os
import hmac
import hashlib
import datetime
from typing import Dict, Any, Optional, List

def get_hmac_key() -> bytes:
    """Load HMAC signing key from environment or fallback key."""
    key_str = os.getenv("LEDGER_HMAC_KEY", "antigravity-finance-hmac-key-v1")
    return key_str.encode("utf-8")

def compute_entry_hash(
    ledger_id: str,
    tool: str,
    inputs: Dict[str, Any],
    raw_value: Any,
    source: str,
    timestamp: str,
    currency: Optional[str] = None,
    unit: Optional[str] = None
) -> str:
    """Compute true HMAC-SHA256 signature of ledger entry fields to detect tampering."""
    serialized_inputs = json.dumps(inputs, sort_keys=True)
    payload = f"{ledger_id}|{tool}|{serialized_inputs}|{raw_value}|{source}|{timestamp}|{currency or ''}|{unit or ''}"
    return hmac.new(get_hmac_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()

class ProvenanceLedger:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.entries: Dict[str, Dict[str, Any]] = {}
        self._counter = 1

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
        unit: Optional[str] = None
    ) -> str:
        """Record a data extraction or calculation in the provenance ledger.
        Generates a unique ledger ID and cryptographic integrity signature.
        """
        ledger_id = f"LEDGER_{self._counter:04d}"
        self._counter += 1
        
        val = raw_value if raw_value is not None else output
        ts = datetime.datetime.now().isoformat()
        
        resolved_ticker = ticker or inputs.get("ticker") or inputs.get("symbol")
        resolved_currency = currency or ("USD" if resolved_ticker == "AAPL" else ("INR" if resolved_ticker and "NS" in resolved_ticker else None))
        resolved_unit = unit or "base"
        
        entry_hash = compute_entry_hash(
            ledger_id=ledger_id,
            tool=tool,
            inputs=inputs,
            raw_value=val,
            source=source,
            timestamp=ts,
            currency=resolved_currency,
            unit=resolved_unit
        )
        
        entry = {
            "ledger_id": ledger_id,
            "tool": tool,
            "ticker": resolved_ticker,
            "currency": resolved_currency,
            "unit": resolved_unit,
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
            unit=entry.get("unit")
        )
        return entry["integrity_hash"] == expected_hash

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
