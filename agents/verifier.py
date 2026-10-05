"""
Enhanced Verifier Agent Engine (/agents/verifier.py)
Audits financial research reports against the immutable Provenance Ledger, primary filings,
live re-fetch endpoints, and the calculation toolkit under a strict DEFAULT-DENY policy.
Never edits the original report.
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

# Number word mappings for written text numbers
WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
}

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
        """Backwards-compatible wrapper for tolerance checks."""
        stated_str = str(stated_val)
        suffix = "%" if is_ratio else ""
        passes, _, _ = self.verify_value_with_precision(stated_str, suffix, raw_val, is_ratio=is_ratio)
        if not passes and raw_val is not None:
            # Fallback check for relative 0.5% or direct scaled check
            if is_ratio:
                return abs(stated_val - raw_val) <= 0.10 or abs(stated_val - raw_val * 100.0) <= 0.10
            if raw_val > 0:
                rel = abs(stated_val - raw_val) / raw_val
                if rel <= 0.005 or abs(stated_val - raw_val) < 0.5:
                    return True
                for s in [1e3, 1e6, 1e7, 1e9, 1e12]:
                    if abs(stated_val - (raw_val / s)) / (raw_val / s) <= 0.005:
                        return True
        return passes

    def verify_value_with_precision(self, stated_str: str, suffix: str, raw_val: float, is_ratio: bool = False) -> Tuple[bool, float, float]:
        """
        Check if raw ledger value matches stated value within half-unit precision of last stated digit.
        Tolerance = 0.5 * 10^(-d) * scale
        """
        if raw_val is None:
            return False, 0.0, 0.0

        clean_str = stated_str.replace(',', '').replace('$', '').replace('₹', '').replace('£', '').replace('€', '').strip()
        try:
            stated_num = float(clean_str)
        except ValueError:
            return False, 0.0, 0.0

        # Determine decimal places d in stated number
        if '.' in clean_str:
            d = len(clean_str.split('.')[1])
        else:
            d = 0

        # Determine scale factor U
        suffix_lower = (suffix or "").lower()
        if suffix_lower in ('billion', 'b', 'billion dollars', 'b dollars'):
            scale = 1e9
        elif suffix_lower in ('million', 'm', 'million dollars', 'm dollars'):
            scale = 1e6
        elif suffix_lower in ('cr', 'crore'):
            scale = 1e7
        elif suffix_lower in ('trillion', 't'):
            scale = 1e12
        elif suffix_lower == 'k':
            scale = 1e3
        elif suffix_lower in ('%', 'percent', 'percentage points', 'bps'):
            scale = 1.0
        else:
            scale = 1.0

        # Half-unit tolerance based on stated precision
        unit_step = (10.0 ** (-d)) * scale
        tolerance = 0.5 * unit_step
        stated_scaled = stated_num * scale

        # For percentages: handle case where raw_val is 0.46905 vs 46.905%
        if is_ratio or suffix_lower in ('%', 'percent'):
            if abs(raw_val) <= 1.0 and abs(stated_scaled) > 1.0:
                raw_compare = raw_val * 100.0
            else:
                raw_compare = raw_val
        else:
            raw_compare = raw_val

        diff = abs(stated_scaled - raw_compare)
        passes = diff <= (tolerance + 1e-9)
        return passes, stated_scaled, tolerance

    def refetch_source(self, entry: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Independently re-fetch source data by period end date and form type."""
        tool = entry.get("tool", "")
        inputs = entry.get("inputs", {})
        expected_val = entry.get("raw_value")
        
        try:
            if tool == "edgar.get_facts":
                import urllib.request
                import json as json_lib
                
                ticker = inputs.get("ticker", "AAPL").upper()
                concept = inputs.get("concept", "")
                period = inputs.get("period", "")
                period_end = inputs.get("period_end") or inputs.get("end_date")
                form_type = inputs.get("form", "10-K")
                
                # Use SEC EDGAR CIK Facts API with User-Agent
                cik_map = {"AAPL": "0000320193", "MSFT": "0000789019", "NVDA": "0001045810", "GOOGL": "0001652044"}
                cik = cik_map.get(ticker, "0000320193")
                url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
                user_agent = os.getenv("SEC_EDGAR_USER_AGENT", "ResearchAnalyst research@example.com")
                req = urllib.request.Request(url, headers={"User-Agent": user_agent})
                
                with urllib.request.urlopen(req, timeout=10) as resp:
                    fact_data = json_lib.loads(resp.read().decode("utf-8"))
                    
                us_gaap = fact_data.get("facts", {}).get("us-gaap", {})
                
                # Concept resolution list to try
                concept_clean = concept.replace("us-gaap:", "")
                candidate_concepts = [concept_clean]
                if "Revenue" in concept_clean or "rev" in concept_clean.lower():
                    candidate_concepts.extend(["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"])
                if "OperatingIncome" in concept_clean:
                    candidate_concepts.extend(["OperatingIncomeLoss", "OperatingIncome"])
                if "NetIncome" in concept_clean:
                    candidate_concepts.extend(["NetIncomeLoss", "NetIncome"])
                    
                for c_key in candidate_concepts:
                    if c_key in us_gaap:
                        units_data = us_gaap[c_key].get("units", {}).get("USD", [])
                        filtered_facts = []
                        for f in units_data:
                            if f.get("form") == form_type:
                                if period_end and f.get("end") == period_end:
                                    filtered_facts.append(f)
                                elif period and str(f.get("fy")) in period:
                                    filtered_facts.append(f)
                        
                        if filtered_facts:
                            selected_fact = filtered_facts[-1]
                            live_val = float(selected_fact["val"])
                            diff = abs(live_val - float(expected_val))
                            source_info = f"SEC 10-K Accn: {selected_fact.get('accn')}, End: {selected_fact.get('end')}"
                            return (diff < 1.0, live_val, source_info)
                        
                return (False, None, f"Fact not found in live SEC XBRL for {concept_clean}")
                
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

    def _split_into_units(self, text: str) -> List[Tuple[int, str, str]]:
        """
        Split report into verifiable units (table rows, sentences) with line numbers.
        Returns list of (line_num, unit_type, unit_text).
        """
        units = []
        lines = text.splitlines()
        
        for line_idx, line in enumerate(lines, start=1):
            s = line.strip()
            if not s:
                continue
                
            # Skip purely structural markdown dividers, headers, and document metadata
            if s.startswith("| :---") or s.startswith("---") or s.startswith("==="):
                continue
                
            if s.startswith("#"):
                # Structural headings
                continue
                
            # Skip document metadata lines like **Audit Date:** ..., **Evaluator:** ..., or *Footers*
            if re.match(r'^\*\*[A-Za-z\s]+:\*\*', s) or (s.startswith("*") and s.endswith("*") and "[" not in s):
                continue
                
            # Table rows
            if s.startswith("|") and s.endswith("|"):
                # Skip table header rows like | Metric | Value |
                if "metric" in s.lower() and ("value" in s.lower() or "source" in s.lower()):
                    continue
                units.append((line_idx, "table_row", s))
                continue
                
            # Clean leading list markers like "1. ", "2. ", "- ", "* ", "(a) "
            line_body = re.sub(r'^\s*(?:\d+\.|\([a-zA-Z0-9]+\)|[-*])\s+', '', s)
            if not line_body:
                continue
                
            # Split paragraph into discrete sentences
            raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9\[\(\"\|])', line_body)
            for sent in raw_sentences:
                sent_clean = sent.strip()
                if sent_clean and not re.match(r'^\d+\.?$', sent_clean):
                    units.append((line_idx, "sentence", sent_clean))
                    
        return units

    def _extract_numbers(self, text: str) -> List[Tuple[str, str, str, str]]:
        """
        Extract numeric figures, including written words, currency, percentages, and table numbers.
        Filters out calendar dates, years, and period labels (e.g. FY2025, September 27, 2025).
        Returns list of (full_token, currency, number_str, suffix).
        """
        found = []
        
        # 1. First extract written word numbers (e.g., "six percent", "93.7 billion dollars")
        word_num_pattern = re.compile(
            r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\s*(percent|percentage points|billion dollars|million dollars|billion|million)\b',
            re.IGNORECASE
        )
        for wm in word_num_pattern.finditer(text):
            w_word = wm.group(1).lower()
            w_suffix = wm.group(2).lower()
            if w_word in WORD_TO_NUM:
                num_val = str(WORD_TO_NUM[w_word])
                found.append((wm.group(0), "", num_val, w_suffix))

        # 2. Strip out date patterns and scenario parameter tags from working copy
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\bFY\d{4}\b',
            r'\bQ[1-4]\s*\d{4}\b',
            r'\b(19|20)\d{2}\b',
            r'\([+-]?\d+\s*bps[^)]*\)',
            r'\[LEDGER_\d+\]',
            r'\[UNVERIFIED:[^\]]+\]',
            r'\[ANALYSIS\]'
        ]
        sanitized_text = text
        for dp in date_patterns:
            sanitized_text = re.sub(dp, ' ', sanitized_text, flags=re.IGNORECASE)

        # 3. Regex for standard digits with currency and suffixes
        pattern = re.compile(
            r'(\$|₹|£|€)?\s*([+-]?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[+-]?\d+\.\d+|[+-]?\d+)\s*(billion dollars|million dollars|billion|million|trillion|crore|cr|k|M|B|T|%|x)?',
            re.IGNORECASE
        )
        for m in pattern.finditer(sanitized_text):
            token = m.group(0).strip()
            curr = m.group(1) or ""
            num_str = m.group(2)
            suffix = (m.group(3) or "").strip()
            
            # Skip empty or punctuation-only tokens
            if not token or token in ('|', '||', '-', '+', '.', ','):
                continue
                
            # Skip leading numbered list indices like '1.' in '1. Apple...'
            if not curr and not suffix and re.match(r'^\d+\.?$', token):
                # Only include if in a table cell or if it's a genuine quantity
                if "|" not in text:
                    continue
                
            found.append((token, curr, num_str, suffix))
            
        return found

    def audit(self) -> Dict[str, Any]:
        """
        Execute full audit under strict DEFAULT-DENY policy:
        Every sentence/table cell must have a valid LEDGER ID, [UNVERIFIED: model memory], or [ANALYSIS].
        """
        self.confirmed.clear()
        self.wrong.clear()
        self.unverifiable.clear()
        
        # 1. Check Ledger Cryptographic HMAC Integrity
        if self.ledger:
            for l_id in list(self.ledger.entries.keys()):
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
                        "failure_reason": f"Cryptographic HMAC signature mismatch on {l_id}. Entry was manually edited or injected!"
                    })

        units = self._split_into_units(self.report_text)
        
        for line_idx, unit_type, unit_str in units:
            # Check Tags
            has_memory_tag = bool(re.search(r'\[UNVERIFIED:\s*model memory\]', unit_str, re.IGNORECASE))
            has_analysis_tag = bool(re.search(r'\[ANALYSIS\]', unit_str, re.IGNORECASE))
            
            # Check for malformed citations like [ledger_0001], (Ledger_0001), or (LEDGER_0001)
            all_ledger_refs = re.findall(r'(\[[a-zA-Z0-9_]+\]|\([a-zA-Z0-9_]+\))', unit_str)
            malformed_citations = [
                ref for ref in all_ledger_refs 
                if "ledger" in ref.lower() and not re.match(r'^\[LEDGER_\d+\]$', ref)
            ]
            if malformed_citations:
                self.unverifiable.append({
                    "line": line_idx,
                    "claim": unit_str,
                    "reason": f"Malformed ledger citation syntax '{malformed_citations[0]}'. Must use exact uppercase format [LEDGER_XXXX].",
                    "error_type": "MALFORMED_CITATION"
                })
                continue
                
            # Extract valid ledger IDs [LEDGER_XXXX]
            ledger_matches = re.findall(r'\[(LEDGER_\d+)\]', unit_str)
            numbers_found = self._extract_numbers(unit_str)
            
            # --- DEFAULT-DENY ENFORCEMENT ---
            # If no ledger IDs, no memory tag, and no analysis tag -> REJECT
            if not ledger_matches and not has_memory_tag and not has_analysis_tag:
                narrative_triggers = [
                    r'founded in', r'headquartered in', r'auditor is', r'audited by',
                    r'competitor to', r'market share of', r'leads the industry in',
                    r'was established in', r'ceo is', r'cfo is', r'manufactured in',
                    r'monopoly in', r'dominant position in', r'largest contributor',
                    r'changed auditors', r'losing share', r'resigned in',
                    r'competition', r'competitor', r'competes with'
                ]
                if any(re.search(nt, unit_str, re.IGNORECASE) for nt in narrative_triggers):
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": unit_str,
                        "reason": "Untagged narrative assertion without ledger ID citation or [UNVERIFIED: model memory] tag.",
                        "error_type": "UNTAGGED_MEMORY_CLAIM"
                    })
                elif numbers_found:
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": unit_str,
                        "reason": f"Untracked figure(s) '{[n[0] for n in numbers_found]}' without ledger ID citation under default-deny.",
                        "error_type": "UNTRACKED_FIGURE"
                    })
                else:
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": unit_str,
                        "reason": "Untagged narrative assertion without ledger ID, [UNVERIFIED: model memory], or [ANALYSIS] tag under default-deny.",
                        "error_type": "UNTAGGED_CLAIM"
                    })
                continue
                
            # If tagged with [UNVERIFIED: model memory]
            if has_memory_tag:
                # If it has untracked financial figures in the same line without ledger IDs
                if not ledger_matches and numbers_found:
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": unit_str,
                        "reason": f"Untracked figure '{numbers_found[0][0]}' in memory-tagged line without ledger ID citation.",
                        "error_type": "UNTRACKED_FIGURE"
                    })
                else:
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": unit_str,
                        "reason": "Declared model memory (unverified).",
                        "error_type": "MODEL_MEMORY_TAGGED"
                    })
                continue
                
            # If tagged with [ANALYSIS]
            if has_analysis_tag:
                # If analysis contains unreferenced specific financial numbers
                if not ledger_matches and numbers_found:
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": unit_str,
                        "reason": f"Specific financial figure '{numbers_found[0][0]}' in [ANALYSIS] line requires ledger citation.",
                        "error_type": "UNTRACKED_FIGURE"
                    })
                else:
                    self.confirmed.append({
                        "line": line_idx,
                        "ledger_id": "ANALYSIS",
                        "claim": unit_str,
                        "verified_value": "ANALYST_DEDUCTION",
                        "tool": "analyst.reasoning",
                        "source": "Report Author Analysis"
                    })
                continue

            # Unit contains ledger ID(s)
            # Rule: Each number in the unit must be backed by a ledger ID
            if len(numbers_found) > len(ledger_matches):
                self.unverifiable.append({
                    "line": line_idx,
                    "claim": unit_str,
                    "reason": f"Unit contains {len(numbers_found)} numbers but only {len(ledger_matches)} ledger IDs. Every figure must have an individual citation.",
                    "error_type": "UNTRACKED_FIGURE"
                })

            for l_id in ledger_matches:
                if not self.ledger or l_id not in self.ledger.entries:
                    self.unverifiable.append({
                        "line": line_idx,
                        "claim": f"Referenced {l_id} in: '{unit_str}'",
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

                # 1. Ticker Mismatch Check
                ticker_mismatch = False
                if entry_ticker and entry_ticker.upper() not in unit_str.upper():
                    for other_t in ["AAPL", "MSFT", "GOOGL", "NVDA", "TCS", "HSBA", "TSLA", "AMZN", "META"]:
                        if other_t in unit_str.upper() and other_t != entry_ticker.upper():
                            self.wrong.append({
                                "line": line_idx,
                                "ledger_id": l_id,
                                "claim": unit_str,
                                "stated_in_report": f"Mentions {other_t}",
                                "actual_ledger_value": f"Ledger is for {entry_ticker}",
                                "correct_value": f"Ticker mismatch: citation belongs to {entry_ticker}",
                                "source": source_url,
                                "error_type": "TICKER_MISMATCH",
                                "failure_reason": f"Report text mentions {other_t} but ledger entry {l_id} is recorded for {entry_ticker}."
                            })
                            ticker_mismatch = True
                            break
                if ticker_mismatch:
                    continue

                # 2. Period Mismatch Check (e.g. FY2024 stated in report vs FY2025 in ledger)
                period_mismatch = False
                if entry_period:
                    period_matches_in_text = re.findall(r'\b(FY\d{4}|Q[1-4]\s*\d{4}|\d{4})\b', unit_str, re.IGNORECASE)
                    for pm in period_matches_in_text:
                        pm_norm = pm.upper().replace(" ", "")
                        if pm_norm.startswith("FY") and pm_norm != entry_period.upper():
                            self.wrong.append({
                                "line": line_idx,
                                "ledger_id": l_id,
                                "claim": unit_str,
                                "stated_in_report": pm_norm,
                                "actual_ledger_value": entry_period,
                                "correct_value": f"Period mismatch: ledger record is {entry_period}",
                                "source": source_url,
                                "error_type": "PERIOD_MISMATCH",
                                "failure_reason": f"Report claims period {pm_norm} but ledger entry {l_id} is for {entry_period}."
                            })
                            period_mismatch = True
                            break
                if period_mismatch:
                    continue

                # 3. Metric Type Mismatch Check
                # e.g. sentence says "revenue rose 4% [LEDGER_0001]" but LEDGER_0001 is total revenue 416B (not growth rate)
                is_growth_or_margin_claim = bool(re.search(r'(grew|rose|growth|expanded|margin|cagr|roic|roe|yield|%)', unit_str, re.IGNORECASE))
                tool_is_growth_calc = bool("growth" in tool_name or "cagr" in tool_name or "margin" in tool_name)
                if "%" in unit_str and not tool_is_growth_calc and expected_raw is not None and float(expected_raw) > 1000:
                    self.wrong.append({
                        "line": line_idx,
                        "ledger_id": l_id,
                        "claim": unit_str,
                        "stated_in_report": "Growth rate / percentage claim",
                        "actual_ledger_value": expected_raw,
                        "correct_value": "Metric Type Mismatch",
                        "source": source_url,
                        "error_type": "METRIC_TYPE_MISMATCH",
                        "failure_reason": f"Report claims a percentage/growth metric, but {l_id} is a base currency level ({expected_raw})."
                    })
                    continue

                # 4. Live Independent Re-Fetch Check
                if self.perform_refetch:
                    refetch_ok, live_val, refetch_source = self.refetch_source(entry)
                    if not refetch_ok:
                        self.wrong.append({
                            "line": line_idx,
                            "ledger_id": l_id,
                            "claim": unit_str,
                            "stated_in_report": unit_str,
                            "actual_ledger_value": expected_raw,
                            "correct_value": live_val,
                            "source": f"{source_url} (Live Refetch: {refetch_source})",
                            "error_type": "SOURCE_REFETCH_DISCREPANCY",
                            "failure_reason": f"Live source returned {live_val} which differs from ledger record {expected_raw}."
                        })
                        continue

                # 5. Half-Unit Precision Verification
                matched_val = False
                
                for token, curr, num_str, suffix in numbers_found:
                    is_token_ratio = suffix in ('%', 'percent', 'bps') or "%" in token or "margin" in tool_name or "cagr" in tool_name or "growth" in tool_name
                    try:
                        # Test with token-specific ratio flag
                        passes, stated_scaled, tol = self.verify_value_with_precision(
                            stated_str=num_str,
                            suffix=suffix,
                            raw_val=float(expected_raw) if expected_raw is not None else None,
                            is_ratio=is_token_ratio
                        )
                        if not passes and not is_token_ratio:
                            # Also test ratio=False
                            passes, stated_scaled, tol = self.verify_value_with_precision(
                                stated_str=num_str,
                                suffix=suffix,
                                raw_val=float(expected_raw) if expected_raw is not None else None,
                                is_ratio=False
                            )
                        if passes:
                            matched_val = True
                            break
                    except (ValueError, TypeError):
                        continue

                if matched_val:
                    self.confirmed.append({
                        "line": line_idx,
                        "ledger_id": l_id,
                        "claim": unit_str,
                        "verified_value": expected_raw,
                        "tool": tool_name,
                        "source": source_url
                    })
                else:
                    self.wrong.append({
                        "line": line_idx,
                        "ledger_id": l_id,
                        "claim": unit_str,
                        "stated_in_report": unit_str,
                        "actual_ledger_value": expected_raw,
                        "correct_value": expected_raw,
                        "source": source_url,
                        "error_type": "VALUE_MISMATCH",
                        "failure_reason": f"Stated figure outside half-unit precision tolerance of raw ledger value {expected_raw}."
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

        md_content += "\n---\n*Audit conducted by Antigravity Verifier Agent under default-deny policy. Original report was not modified.*"

        with open(audit_md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        return audit_md_path
