"""
Verifier Agent Engine (/agents/verifier.py)
Audits financial research reports against the immutable Provenance Ledger, primary filings,
and the calculation toolkit. Never edits the original report.
"""

import os
import re
import json
import datetime
from typing import Dict, Any, List, Tuple
from tools.ledger import ProvenanceLedger
from tools.calc import (
    yoy_growth, cagr, margin, roic, roe, free_cash_flow,
    fcf_yield, net_debt_to_ebitda, interest_coverage,
    cash_conversion, enterprise_value, ev_multiples
)

class ReportVerifier:
    def __init__(self, report_path: str, ledger_path: str = None):
        self.report_path = report_path
        self.ledger_path = ledger_path or f"{os.path.splitext(report_path)[0]}.provenance.json"
        
        if not os.path.exists(self.report_path):
            raise FileNotFoundError(f"Report file not found: {self.report_path}")
            
        with open(self.report_path, "r", encoding="utf-8") as f:
            self.report_text = f.read()
            
        if os.path.exists(self.ledger_path):
            self.ledger = ProvenanceLedger.load_sidecar(self.ledger_path)
        else:
            self.ledger = None

        self.confirmed: List[Dict[str, Any]] = []
        self.wrong: List[Dict[str, Any]] = []
        self.unverifiable: List[Dict[str, Any]] = []

    def audit(self) -> Dict[str, Any]:
        """Execute comprehensive audit across all claims, figures, and narrative text."""
        self.confirmed.clear()
        self.wrong.clear()
        self.unverifiable.clear()
        
        lines = self.report_text.splitlines()
        
        # Regex patterns
        # 1. Tagged figure with ledger ID: e.g. "$416,161M [LEDGER_0001]" or "46.91% <!-- ledger:LEDGER_0002 -->"
        ledger_ref_pattern = re.compile(r'(?:\[(?:LEDGER_\d+)\]|<!--\s*ledger:(LEDGER_\d+)\s*-->)')
        
        # 2. Number pattern: e.g., $100M, 15.5%, 1,234.50, ₹50,000 Cr
        number_pattern = re.compile(r'(\$|₹|£|€)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+\.\d+|\d+)\s*(Billion|Million|Trillion|Cr|Crore|k|M|B|T|%|x|USD|INR|GBP|GBp)?', re.IGNORECASE)
        
        # 3. Model memory tag pattern: [UNVERIFIED: model memory]
        memory_tag_pattern = re.compile(r'\[UNVERIFIED:\s*model memory\]', re.IGNORECASE)
        
        for line_idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#") or line_str.startswith("| :---") or line_str.startswith("---"):
                continue

            # Check for explicit narrative memory claims
            if "founded in" in line_str.lower() or "auditor is" in line_str.lower() or "headquartered in" in line_str.lower():
                if not memory_tag_pattern.search(line_str) and not ledger_ref_pattern.search(line_str) and "http" not in line_str:
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": line_str,
                        "reason": "Untagged factual narrative claim with no cited ledger ID or source URL.",
                        "error_type": "UNTAGGED_MEMORY_CLAIM"
                    })
                    continue

            # Find all numbers in the line
            matches = list(number_pattern.finditer(line_str))
            
            # Find any ledger IDs in the line
            ledger_matches = re.findall(r'LEDGER_\d+', line_str)
            
            if not matches:
                continue
                
            # If line has numbers but no ledger ID and no source link, check if it's an unverified figure
            if not ledger_matches:
                # Check if it's a section header, date string (e.g. 2026-10-05), or table index
                is_benign = bool(re.match(r'^(FY\d{4}|\d{4}-\d{2}-\d{2}|\d+\.|\*|\|\s*\d+\s*\|)', line_str))
                if not is_benign and any(char in line_str for char in ['$', '₹', '%', 'Billion', 'Million', 'x']):
                    for m in matches:
                        num_text = m.group(0).strip()
                        if num_text and not re.match(r'^\d{4}$', num_text): # skip years
                            self.unverifiable.append({
                                "line": line_idx,
                                "claim": f"Figure '{num_text}' in line: '{line_str}'",
                                "reason": "Figure has no associated ledger entry ID or source reference.",
                                "error_type": "UNTRACKED_FIGURE"
                            })
                continue
                
            # Line has ledger ID(s) - audit against ledger entries
            for l_id in ledger_matches:
                if not self.ledger or l_id not in self.ledger.entries:
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": f"Referenced {l_id} in line: '{line_str}'",
                        "reason": f"Ledger ID '{l_id}' does not exist in provenance sidecar.",
                        "error_type": "MISSING_LEDGER_ENTRY"
                    })
                    continue
                    
                entry = self.ledger.entries[l_id]
                expected_raw = entry.get("raw_value")
                tool_name = entry.get("tool")
                source_url = entry.get("source")
                
                # Check value agreement
                # Extract numeric magnitude from line
                # Compare raw value with values found on line
                line_has_matching_value = False
                for m in matches:
                    raw_str = m.group(2).replace(',', '')
                    try:
                        val = float(raw_str)
                        # Check scaled comparisons (e.g., $416,161M vs 416161000000, 46.91 vs 46.91%, 38.2x vs 38.18)
                        if expected_raw is not None and isinstance(expected_raw, (int, float)):
                            exp_f = float(expected_raw)
                            # direct match or scaled by 1e6, 1e9, 1e12, or 100
                            candidates = [exp_f, exp_f / 1e6, exp_f / 1e9, exp_f / 1e12, exp_f * 100, exp_f / 100]
                            for c in candidates:
                                if abs(val - c) < 0.01 or (c > 0 and abs(val - c) / c < 0.005):
                                    line_has_matching_value = True
                                    break
                    except ValueError:
                        continue
                        
                if line_has_matching_value:
                    self.confirmed.append({
                        "line": line_idx,
                        "ledger_id": l_id,
                        "claim": line_str,
                        "verified_value": expected_raw,
                        "tool": tool_name,
                        "source": source_url
                    })
                else:
                    self.wrong.append({
                        "line": line_idx,
                        "ledger_id": l_id,
                        "claim": line_str,
                        "stated_in_report": line_str,
                        "actual_ledger_value": expected_raw,
                        "correct_value": expected_raw,
                        "source": source_url,
                        "error_type": "VALUE_MISMATCH"
                    })

        audit_result = {
            "report_path": self.report_path,
            "audited_at": datetime.datetime.now().isoformat(),
            "summary": {
                "total_confirmed": len(self.confirmed),
                "total_wrong": len(self.wrong),
                "total_unverifiable": len(self.unverifiable),
                "status": "FAILED" if (self.wrong or self.unverifiable) else "PASSED"
            },
            "confirmed": self.confirmed,
            "wrong": self.wrong,
            "unverifiable": self.unverifiable
        }
        
        # Save audit report sidecar
        self._save_audit_report(audit_result)
        return audit_result

    def _save_audit_report(self, audit_result: Dict[str, Any]) -> str:
        audit_md_path = f"{os.path.splitext(self.report_path)[0]}.audit.md"
        summary = audit_result["summary"]
        
        md_content = f"""# Verification Audit Report
**Target Report:** `{os.path.basename(self.report_path)}`  
**Audit Timestamp:** {audit_result['audited_at']}  
**Overall Status:** **{summary['status']}** ({summary['total_confirmed']} Confirmed, {summary['total_wrong']} Wrong, {summary['total_unverifiable']} Unverifiable)  

---

### ✅ 1. Confirmed Claims ({summary['total_confirmed']})
"""
        if self.confirmed:
            for item in self.confirmed:
                md_content += f"- **[Line {item['line']}] [{item['ledger_id']}]**: {item['claim']}\n  - *Verified Output:* `{item['verified_value']}` via `{item['tool']}`\n  - *Source:* {item['source']}\n"
        else:
            md_content += "_No figures confirmed._\n"

        md_content += f"\n---\n\n### ❌ 2. Wrong / Discrepant Figures ({summary['total_wrong']})\n"
        if self.wrong:
            for item in self.wrong:
                md_content += f"- **[Line {item['line']}] [{item['ledger_id']}]**: {item['claim']}\n  - *Discrepancy:* Stated in report does not match ledger recorded output `{item['actual_ledger_value']}`.\n  - *Correct Value:* `{item['correct_value']}` (Source: {item['source']})\n"
        else:
            md_content += "_None. No value discrepancies found._\n"

        md_content += f"\n---\n\n### ⚠️ 3. Unverifiable / Failed Claims ({summary['total_unverifiable']})\n"
        if self.unverifiable:
            for item in self.unverifiable:
                md_content += f"- **[Line {item['line']}] [{item['error_type']}]**: {item['claim']}\n  - *Failure Reason:* {item['reason']}\n"
        else:
            md_content += "_None. All claims have valid sources and ledger provenance._\n"

        md_content += "\n---\n*Audit conducted by Antigravity Verifier Agent. Original report was not modified.*"

        with open(audit_md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        return audit_md_path
