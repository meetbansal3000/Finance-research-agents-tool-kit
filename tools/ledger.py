"""
Provenance Ledger System
Tracks every financial data extraction and calculation with an immutable ledger ID,
source URL, input parameters, timestamp, and raw output.
"""

import json
import os
import datetime
from typing import Dict, Any, Optional, List

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
        notes: Optional[str] = None
    ) -> str:
        """Record a data extraction or calculation in the provenance ledger.
        Returns the unique ledger ID (e.g., 'LEDGER_001').
        """
        ledger_id = f"LEDGER_{self._counter:04d}"
        self._counter += 1
        
        entry = {
            "ledger_id": ledger_id,
            "tool": tool,
            "inputs": inputs,
            "output": output,
            "raw_value": raw_value if raw_value is not None else output,
            "source": source,
            "form": form,
            "period": period,
            "notes": notes,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.entries[ledger_id] = entry
        return ledger_id

    def get(self, ledger_id: str) -> Optional[Dict[str, Any]]:
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
            max_id = max([int(k.split("_")[-1]) for k in instance.entries.keys() if "_" in k] or [0])
            instance._counter = max_id + 1
        return instance
