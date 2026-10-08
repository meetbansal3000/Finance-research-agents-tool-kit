"""
agents/nvidia_agent.py - NVIDIA NIM Accelerated Research Agent
Specialist multi-agent committee member providing high-velocity cognitive reasoning,
multi-model consensus analysis (Nemotron 70B + Llama 3.1 70B + Mixtral 8x22B),
adversarial stress testing, and unstructured footnote auditing.

Fully integrated with:
  - ProvenanceLedger (source_tag='NVIDIA_NIM_INFERENCE')
  - SkepticAgent & AnalystAgent committee workflow
  - Deterministic offline recovery mode
"""

import os
import re
import datetime
from typing import Dict, Any, List, Optional

from tools.ledger import ProvenanceLedger
from tools.nvidia_client import NvidiaNimClient, DEFAULT_MODEL, SUPPORTED_MODELS


class NvidiaResearchAgent:
    """NVIDIA-powered cognitive research agent for investment thesis acceleration."""

    def __init__(
        self,
        ledger: Optional[ProvenanceLedger] = None,
        client: Optional[NvidiaNimClient] = None,
        default_model: str = DEFAULT_MODEL,
    ):
        self.ledger = ledger or ProvenanceLedger(
            run_id=f"nvidia_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.client = client or NvidiaNimClient(default_model=default_model)
        self.default_model = default_model

    def is_accelerated(self) -> bool:
        """Returns True if live NVIDIA cloud microservices are active."""
        return self.client.is_configured()

    def run_adversarial_critique(
        self,
        ticker: str,
        metrics: Dict[str, Any],
        thesis_text: str,
    ) -> Dict[str, Any]:
        """
        Execute accelerated adversarial stress-test critique on an investment thesis.
        Anchors output directly into the ProvenanceLedger.
        """
        result = self.client.generate_adversarial_critique(
            ticker=ticker,
            metrics=metrics,
            thesis_text=thesis_text,
            ledger=self.ledger,
        )
        return {
            "ticker": ticker,
            "critique_text": result["content"],
            "model": result["model"],
            "ledger_id": result["ledger_id"],
            "latency_ms": result["latency_ms"],
            "offline_fallback": result["offline_fallback"],
        }

    def audit_footnote_disclosures(
        self,
        ticker: str,
        footnote_text: str,
        focus_topic: str = "Customer Concentration",
    ) -> Dict[str, Any]:
        """
        Parse and evaluate complex unstructured SEC footnote disclosures (ASC 280, ASC 842).
        Anchors reasoning and extracted percentages into the ProvenanceLedger.
        """
        result = self.client.parse_qualitative_disclosures(
            ticker=ticker,
            footnote_text=footnote_text,
            focus_topic=focus_topic,
            ledger=self.ledger,
        )

        content = result["content"]
        # Extract detected percentage if present
        pct_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*%', content)
        detected_pct = float(pct_match.group(1)) if pct_match else None

        has_concentration = None
        is_div = ("diversified" in content.lower() or "no single customer" in content.lower() or "low / diversified" in content.lower() or "<10%" in content)
        if is_div:
            has_concentration = False
            detected_pct = 0.0
        elif detected_pct is not None:
            has_concentration = detected_pct >= 10.0

        return {
            "ticker": ticker,
            "focus_topic": focus_topic,
            "analysis_text": content,
            "detected_pct": detected_pct,
            "has_concentration_above_10": has_concentration,
            "ledger_id": result["ledger_id"],
            "model": result["model"],
            "latency_ms": result["latency_ms"],
            "offline_fallback": result["offline_fallback"],
        }

    def synthesize_committee_memo(
        self,
        ticker: str,
        analyst_report: str,
        skeptic_report: str,
        valuation_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize unified executive investment committee memo combining Analyst valuation
        and Skeptic adversarial counter-evidence.
        """
        system_prompt = (
            "You are the Chairman of an Institutional Investment Committee. "
            "Synthesize the Analyst Bull Case and Skeptic Bear Case into an actionable, "
            "rigorous executive memorandum. Enforce zero tolerance for ungrounded claims."
        )
        val_snippet = ""
        if valuation_summary:
            val_snippet = (
                f"\nValuation Summary:\n"
                f"- Fair Value: {valuation_summary.get('fair_value', 'N/A')}\n"
                f"- Market Price: {valuation_summary.get('current_price', 'N/A')}\n"
                f"- Implied Growth: {valuation_summary.get('implied_growth', 'N/A')}%\n"
            )

        user_prompt = (
            f"Produce an Institutional Investment Committee Memo for {ticker}.\n\n"
            f"{val_snippet}\n"
            f"### ANALYST REPORT SUMMARY:\n{analyst_report[:1200]}\n\n"
            f"### SKEPTIC ADVERSARIAL REPORT SUMMARY:\n{skeptic_report[:1200]}\n\n"
            f"Generate a clear markdown memorandum containing:\n"
            f"1. Executive Decision Summary\n"
            f"2. Core Valuation Grounding\n"
            f"3. Key Vulnerabilities & Stress Scenarios\n"
            f"4. Monitoring Checklist for Upcoming Filings"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = self.client.chat_completion(
            messages=messages,
            model=self.default_model,
            temperature=0.2,
            ledger=self.ledger,
            ticker=ticker,
            task_label="committee_synthesis",
        )

        return {
            "ticker": ticker,
            "memo_markdown": result["content"],
            "ledger_id": result["ledger_id"],
            "model": result["model"],
            "latency_ms": result["latency_ms"],
            "offline_fallback": result["offline_fallback"],
        }

    def generate_multi_model_consensus(
        self,
        ticker: str,
        thesis_prompt: str,
        models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute multi-model cross-examination across multiple NVIDIA NIM architectures
        (e.g., Nemotron 70B, Llama 3.1 70B, Mixtral 8x22B) to eliminate single-model bias.
        """
        target_models = models or [
            "nvidia/nemotron-3-ultra-550b-a55b",
            "nvidia/nemotron-3.5-lightning-30b-a3b",
            "meta/llama-3.1-70b-instruct",
        ]

        responses: Dict[str, Any] = {}
        for m in target_models:
            res = self.client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a rigorous financial researcher. Evaluate the investment question "
                            "based strictly on audited quantitative facts and capital efficiency metrics."
                        ),
                    },
                    {"role": "user", "content": thesis_prompt},
                ],
                model=m,
                temperature=0.2,
                ledger=self.ledger,
                ticker=ticker,
                task_label=f"consensus_{m.replace('/', '_')}",
            )
            responses[m] = {
                "content": res["content"],
                "ledger_id": res["ledger_id"],
                "latency_ms": res["latency_ms"],
                "offline": res["offline_fallback"],
            }

        return {
            "ticker": ticker,
            "models_queried": target_models,
            "responses": responses,
            "ledger": self.ledger,
        }
