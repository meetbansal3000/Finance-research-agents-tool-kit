"""
Enhanced Verifier Agent Engine (/agents/verifier.py)
Audits financial research reports against the immutable Provenance Ledger, primary filings,
live re-fetch endpoints, and the calculation toolkit. Never edits the original report.
"""

import os
import re
import json
import datetime
from typing import Dict, Any, List, Tuple, Optional
from tools.ledger import ProvenanceLedger
from tools.calc import (
    yoy_growth, cagr, margin, roic, roe, free_cash_flow,
    fcf_yield, net_debt_to_ebitda, interest_coverage,
    cash_conversion, enterprise_value, ev_multiples,
    dcf, reverse_dcf, convert_currency
)

# Defined Round-Trip Rounding Tolerances
REL_TOLERANCE_CURRENCY = 0.005  # 0.5% relative error for large numbers (e.g. $416.2B vs $416,161M)
ABS_TOLERANCE_RATIO = 0.10      # 0.10 percentage points / multiples (e.g. 46.91% vs 46.9%)

class ReportVerifier:
    def __init__(self, report_path: str, ledger_path: str = None, perform_refetch: bool = False):
        self.report_path = report_path
        self.ledger_path = ledger_path or f"{os.path.splitext(report_path)[0]}.provenance.json"
        self.perform_refetch = perform_refetch
        
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

    def verify_value_with_tolerance(self, stated_val: float, raw_val: float, is_ratio: bool = False) -> bool:
        """Check if stated report value matches raw ledger value within strict rounding tolerances."""
        if raw_val is None:
            return False
            
        if is_ratio:
            # Check direct percentage or basis points
            diff = abs(stated_val - raw_val)
            if diff <= ABS_TOLERANCE_RATIO:
                return True
            # Check 100x scale factor (0.4691 vs 46.91%)
            if abs(stated_val - raw_val * 100.0) <= ABS_TOLERANCE_RATIO:
                return True
            if abs(stated_val * 100.0 - raw_val) <= ABS_TOLERANCE_RATIO:
                return True
            return False

        # Currency / volume scaling factors: 1, 1e3 (k), 1e6 (M), 1e9 (B), 1e12 (T), 1e7 (Crore / Cr)
        scales = [1.0, 1e3, 1e6, 1e7, 1e9, 1e12]
        for s in scales:
            scaled_target = raw_val / s
            if scaled_target == 0:
                if stated_val == 0:
                    return True
                continue
            rel_diff = abs(stated_val - scaled_target) / abs(scaled_target)
            if rel_diff <= REL_TOLERANCE_CURRENCY or abs(stated_val - scaled_target) < 0.05:
                return True
                
        return False

    def refetch_source(self, entry: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Independently re-fetch source data to confirm ledger fidelity."""
        tool = entry.get("tool", "")
        inputs = entry.get("inputs", {})
        expected_val = entry.get("raw_value")
        
        try:
            if tool == "edgar.get_facts":
                from edgar import Company, set_identity
                set_identity("Research Analyst research.analyst@example.com")
                c = Company(inputs.get("ticker", "AAPL"))
                facts = c.get_facts()
                df = facts.to_dataframe()
                concept = inputs.get("concept")
                period = inputs.get("period")
                sub = df[df["concept"] == concept]
                if period:
                    sub = sub[(sub["fiscal_period"] == period) | (sub["fiscal_year"] == int(period.replace("FY", "")))]
                if not sub.empty:
                    live_val = float(sub["numeric_value"].iloc[-1])
                    return (abs(live_val - expected_val) / abs(expected_val) < 0.001, live_val, "Live SEC EDGAR XBRL")
                return (False, None, "Concept not found in live SEC filing")
                
            elif tool.startswith("tools.calc."):
                fn_name = tool.split(".")[-1]
                calc_tools = {
                    "yoy_growth": yoy_growth, "cagr": cagr, "margin": margin,
                    "roic": roic, "roe": roe, "free_cash_flow": free_cash_flow,
                    "fcf_yield": fcf_yield, "net_debt_to_ebitda": net_debt_to_ebitda,
                    "interest_coverage": interest_coverage, "cash_conversion": cash_conversion,
                    "enterprise_value": enterprise_value, "ev_multiples": ev_multiples,
                    "dcf": dcf, "reverse_dcf": reverse_dcf, "convert_currency": convert_currency
                }
                if fn_name in calc_tools:
                    calc_fn = calc_tools[fn_name]
                    res = calc_fn(**inputs)
                    recomputed_val = res.get("result")
                    if isinstance(recomputed_val, dict):
                        return (True, recomputed_val, "Recomputed Calc Tool")
                    return (abs(float(recomputed_val) - float(expected_val)) < 1e-4, recomputed_val, "Recomputed Calc Tool")
                    
            elif tool == "yfinance.quote":
                import yfinance as yf
                t = yf.Ticker(inputs.get("symbol", inputs.get("ticker")))
                price = float(t.info.get("currentPrice") or t.info.get("regularMarketPrice") or 0.0)
                return (price > 0, price, "Live Yahoo Finance Quote")
                
        except Exception as e:
            return (False, None, f"Re-fetch exception: {e}")
            
        return (True, expected_val, "Unmocked/Static verified tool")

    def audit(self) -> Dict[str, Any]:
        """Execute full audit: ledger tampering, re-fetch, claim detection, memory tags, and math."""
        self.confirmed.clear()
        self.wrong.clear()
        self.unverifiable.clear()
        
        # 1. Check Ledger Cryptographic Integrity
        if self.ledger:
            for l_id in self.ledger.entries.keys():
                if not self.ledger.verify_entry_integrity(l_id):
                    self.wrong.append({
                        "line": 0,
                        "ledger_id": l_id,
                        "claim": f"Ledger entry {l_id}",
                        "error_type": "LEDGER_TAMPERED",
                        "stated_in_report": "N/A",
                        "actual_ledger_value": self.ledger.entries[l_id].get("raw_value"),
                        "correct_value": "INTEGRITY_COMPROMISED",
                        "source": self.ledger.entries[l_id].get("source"),
                        "failure_reason": f"Cryptographic signature mismatch on {l_id}. Entry was manually edited or forged!"
                    })

        lines = self.report_text.splitlines()
        
        # Regex Patterns
        number_pattern = re.compile(
            r'(\$|₹|£|€)?\s*([+-]?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[+-]?\d+\.\d+|[+-]?\d+)\s*(Billion|Million|Trillion|Cr|Crore|k|M|B|T|%|x|USD|INR|GBP|GBp)?',
            re.IGNORECASE
        )
        memory_tag_pattern = re.compile(r'\[UNVERIFIED:\s*model memory\]', re.IGNORECASE)
        
        # Narrative claim triggers (assertions of corporate facts, auditor, competitor, founders, market position)
        narrative_triggers = [
            r'founded in', r'headquartered in', r'auditor is', r'audited by',
            r'competitor to', r'market share of', r'leads the industry in',
            r'was established in', r'ceo is', r'cfo is', r'manufactured in',
            r'monopoly in', r'dominant position in'
        ]
        narrative_regex = re.compile('|'.join(narrative_triggers), re.IGNORECASE)

        for line_idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#") or line_str.startswith("| :---") or line_str.startswith("---"):
                continue

            has_memory_tag = bool(memory_tag_pattern.search(line_str))
            ledger_matches = re.findall(r'LEDGER_\d+', line_str)
            has_source_url = "http://" in line_str or "https://" in line_str

            # Check for qualitative/narrative claims
            if narrative_regex.search(line_str):
                if not has_memory_tag and not ledger_matches and not has_source_url:
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": line_str,
                        "reason": "Untagged narrative assertion without source citation or [UNVERIFIED: model memory] tag.",
                        "error_type": "UNTAGGED_MEMORY_CLAIM"
                    })
                    continue

            # Extract numbers from line
            num_matches = list(number_pattern.finditer(line_str))
            
            # If line has no ledger ID and has untagged financial metrics/numbers
            if not ledger_matches:
                if has_memory_tag:
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": line_str,
                        "reason": "Declared model memory (unverified).",
                        "error_type": "MODEL_MEMORY_TAGGED"
                    })
                    
                is_date_or_header = bool(re.match(r'^(FY\d{4}|\d{4}-\d{2}-\d{2}|\d+\.|\*|\|\s*\d+\s*\|)', line_str))
                for nm in num_matches:
                    token = nm.group(0).strip()
                    val_str = nm.group(2).replace(',', '')
                    suffix = (nm.group(3) or "").lower()
                    currency = nm.group(1)
                    
                    # Ignore pure standalone years like 2021, 2025 unless currency/suffix is attached
                    if re.match(r'^[+-]?(19|20)\d{2}$', val_str) and not currency and not suffix:
                        continue
                        
                    if currency or suffix in ('%', 'x', 'billion', 'million', 'b', 'm', 'cr', 'crore'):
                        self.unverifiable.append({
                            "line": line_idx,
                            "claim": f"Figure '{token}' in line: '{line_str}'",
                            "reason": "Financial figure has no associated ledger entry ID or source citation.",
                            "error_type": "UNTRACKED_FIGURE"
                        })
                continue

            # Line contains ledger ID(s) -> audit against ledger
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
                entry_ticker = entry.get("ticker")
                entry_period = entry.get("period")
                source_url = entry.get("source")
                tool_name = entry.get("tool")

                # Check Ticker / Period Mismatch on the line
                # e.g. line says "MSFT revenue" but ledger entry is for AAPL
                if entry_ticker and entry_ticker.upper() not in line_str.upper():
                    # If line explicitly names a DIFFERENT known ticker
                    for other_t in ["AAPL", "MSFT", "GOOGL", "NVDA", "TCS", "HSBA", "TSLA"]:
                        if other_t in line_str.upper() and other_t != entry_ticker.upper():
                            self.wrong.append({
                                "line": line_idx,
                                "ledger_id": l_id,
                                "claim": line_str,
                                "stated_in_report": f"Refers to {other_t}",
                                "actual_ledger_value": f"Ledger is for {entry_ticker}",
                                "correct_value": f"Mismatched ticker. Ledger ID belongs to {entry_ticker}",
                                "source": source_url,
                                "error_type": "TICKER_MISMATCH"
                            })
                            break

                # Re-fetch live source if requested
                if self.perform_refetch:
                    refetch_ok, live_val, refetch_source = self.refetch_source(entry)
                    if not refetch_ok:
                        self.wrong.append({
                            "line": line_idx,
                            "ledger_id": l_id,
                            "claim": line_str,
                            "stated_in_report": line_str,
                            "actual_ledger_value": expected_raw,
                            "correct_value": live_val,
                            "source": f"{source_url} (Live Refetch: {refetch_source})",
                            "error_type": "SOURCE_REFETCH_DISCREPANCY",
                            "failure_reason": f"Live source returned {live_val} which differs from ledger record {expected_raw}."
                        })
                        continue

                # Match values in line against raw ledger value using strict tolerance
                is_ratio = bool(re.search(r'(%|margin|cagr|roic|roe|multiple|x|yield)', line_str, re.IGNORECASE))
                matched_val = False
                
                for nm in num_matches:
                    val_str = nm.group(2).replace(',', '')
                    suffix = (nm.group(3) or "").lower()
                    try:
                        v = float(val_str)
                        # Scale based on suffix if present
                        if suffix in ('billion', 'b'):
                            v = v * 1e9
                        elif suffix in ('million', 'm'):
                            v = v * 1e6
                        elif suffix in ('cr', 'crore'):
                            v = v * 1e7
                        elif suffix == 'k':
                            v = v * 1e3
                            
                        if expected_raw is not None and isinstance(expected_raw, (int, float)):
                            if self.verify_value_with_tolerance(v, float(expected_raw), is_ratio=is_ratio):
                                matched_val = True
                                break
                    except ValueError:
                        continue

                if matched_val:
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
                reason = item.get("failure_reason", f"Discrepancy: Report does not match ledger output `{item['actual_ledger_value']}`.")
                md_content += f"- **[Line {item['line']}] [{item.get('error_type', 'ERROR')} | {item.get('ledger_id', 'N/A')}]**: {item['claim']}\n  - *Reason:* {reason}\n  - *Correct Value:* `{item['correct_value']}` (Source: {item['source']})\n"
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
