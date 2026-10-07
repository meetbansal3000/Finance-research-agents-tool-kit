"""
tests/test_nvidia_agent.py - Comprehensive Unit & Integration Tests for NVIDIA Agents
Tests:
  - NvidiaNimClient initialization, model registry, and configuration detection
  - Deterministic offline fallback reasoning (zero failure in offline/keyless environments)
  - Cryptographic ProvenanceLedger anchoring (source_tag='NVIDIA_NIM_INFERENCE')
  - Adversarial stress testing via Nemotron 70B
  - Unstructured SEC footnote disclosure auditing (ASC 280 customer concentration)
  - Multi-model consensus cross-examination
  - Integration with SkepticAgent adversarial reports
"""

import os
import pytest
from tools.ledger import ProvenanceLedger
from tools.nvidia_client import NvidiaNimClient, DEFAULT_MODEL, SUPPORTED_MODELS
from agents.nvidia_agent import NvidiaResearchAgent
from agents.skeptic import SkepticAgent


def test_nvidia_client_init_and_supported_models():
    """Verify client instantiates cleanly and exposes supported models."""
    client = NvidiaNimClient(api_key="", offline_mode=True)
    assert not client.is_configured()
    assert client.default_model == DEFAULT_MODEL
    models = client.get_supported_models()
    assert "nvidia/llama-3.1-nemotron-70b-instruct" in models
    assert "meta/llama-3.1-70b-instruct" in models


def test_nvidia_deterministic_offline_completion():
    """Verify deterministic financial reasoning operates reliably without API keys."""
    client = NvidiaNimClient(api_key="", offline_mode=True)
    ledger = ProvenanceLedger(run_id="test_nvidia_run")

    messages = [
        {"role": "system", "content": "You are a quantitative research assistant."},
        {"role": "user", "content": "Analyze the financial results and valuation for NVDA."},
    ]

    res = client.chat_completion(
        messages=messages,
        ledger=ledger,
        ticker="NVDA",
        task_label="test_completion",
    )

    assert res["offline_fallback"] is True
    assert "NVDA" in res.get("content", "") or "Quantitative" in res.get("content", "")
    assert res["ledger_id"] is not None
    assert res["usage"]["total_tokens"] > 0
    assert res["latency_ms"] >= 0

    # Verify ProvenanceLedger entry
    entry = ledger.get_entry(res["ledger_id"])
    assert entry is not None
    assert entry["source_tag"] == "NVIDIA_NIM_INFERENCE"
    assert "NVIDIA NIM" in entry["source"]


def test_nvidia_adversarial_critique_generation():
    """Verify adversarial critique method produces structured Bear Case stress points."""
    client = NvidiaNimClient(api_key="", offline_mode=True)
    ledger = ProvenanceLedger()

    metrics = {
        "revenue_growth_pct": 25.0,
        "operating_margin_pct": 35.0,
        "fcf": "$15,000M",
        "net_debt": "$5,000M",
        "implied_growth_pct": 18.5,
    }

    critique = client.generate_adversarial_critique(
        ticker="AAPL",
        metrics=metrics,
        thesis_text="Thesis assuming persistent 25% revenue growth and peak operating margins.",
        ledger=ledger,
    )

    content = critique["content"]
    assert "Adversarial Stress-Test Critique" in content
    assert "Deceleration" in content or "Margin" in content
    assert critique["ledger_id"] is not None

    entry = ledger.get_entry(critique["ledger_id"])
    assert entry["source_tag"] == "NVIDIA_NIM_INFERENCE"


def test_nvidia_footnote_concentration_parsing():
    """Verify parsing of unstructured SEC 10-K note disclosures."""
    client = NvidiaNimClient(api_key="", offline_mode=True)
    ledger = ProvenanceLedger()

    footnote_high_conc = (
        "Note 19 - Concentration of Risk: During fiscal 2025, Customer A accounted for 22% "
        "of consolidated net revenues. No other customer accounted for 10% or more."
    )

    res_high = client.parse_qualitative_disclosures(
        ticker="NVDA",
        footnote_text=footnote_high_conc,
        focus_topic="Customer Concentration",
        ledger=ledger,
    )

    assert "22" in res_high["content"]
    assert "HIGH CONCENTRATION" in res_high["content"]

    # Test diversified note
    footnote_div = (
        "Note 12 - Segment Information: The company has a diversified customer base and "
        "no single customer accounted for 10% or more of net revenues in any period presented."
    )

    res_div = client.parse_qualitative_disclosures(
        ticker="AAPL",
        footnote_text=footnote_div,
        focus_topic="Customer Concentration",
        ledger=ledger,
    )

    assert "DIVERSIFIED" in res_div["content"]


def test_nvidia_research_agent_methods():
    """Verify full NvidiaResearchAgent specialist capabilities."""
    agent = NvidiaResearchAgent()
    assert agent.client is not None

    # 1. Adversarial Critique
    adv_res = agent.run_adversarial_critique(
        ticker="MSFT",
        metrics={"revenue_growth_pct": 14.0, "operating_margin_pct": 44.0},
        thesis_text="Cloud expansion thesis assuming continuous margin expansion.",
    )
    assert adv_res["ticker"] == "MSFT"
    assert adv_res["ledger_id"] is not None

    # 2. Footnote Audit
    audit_res = agent.audit_footnote_disclosures(
        ticker="MSFT",
        footnote_text="Customer Concentration: No single customer represented greater than 10% of revenue.",
    )
    assert audit_res["ticker"] == "MSFT"
    assert audit_res["has_concentration_above_10"] is False

    # 3. Committee Memo Synthesis
    memo_res = agent.synthesize_committee_memo(
        ticker="MSFT",
        analyst_report="Bull Case: Fair Value $480 based on 15% EPS CAGR.",
        skeptic_report="Bear Case: Multiple compression risk if AI capex payoff lags.",
        valuation_summary={"fair_value": "$480", "current_price": "$420", "implied_growth": 12.0},
    )
    assert memo_res["ticker"] == "MSFT"
    assert "memo_markdown" in memo_res
    assert memo_res["ledger_id"] is not None


def test_nvidia_multi_model_consensus():
    """Verify multi-model cross-examination across multiple model architectures."""
    agent = NvidiaResearchAgent()
    consensus = agent.generate_multi_model_consensus(
        ticker="NVDA",
        thesis_prompt="Evaluate durability of data center compute moat under sovereign AI demand.",
        models=[
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "meta/llama-3.1-70b-instruct",
        ],
    )

    assert consensus["ticker"] == "NVDA"
    assert len(consensus["models_queried"]) == 2
    for model_name in consensus["models_queried"]:
        assert model_name in consensus["responses"]
        resp_obj = consensus["responses"][model_name]
        assert resp_obj["ledger_id"] is not None


def test_skeptic_agent_with_nvidia_enabled():
    """Verify SkepticAgent seamlessly enriches its adversarial review when NVIDIA is enabled."""
    skeptic = SkepticAgent()
    res = skeptic.evaluate_thesis(
        ticker="NVDA",
        current_price=120.0,
        shares_outstanding=24500000000.0,
        base_fcf=27000000000.0,
        base_operating_margin=0.55,
        stated_growth_rate=0.20,
        enable_nvidia=True,
    )

    assert res["verdict"] in ("ROBUST / NO STRONG COUNTER-EVIDENCE FOUND", "VULNERABLE / STRETCHED", "INCONCLUSIVE")
    assert res.get("nvidia_critique") is not None
    assert res.get("nvidia_ledger_id") is not None
    assert "NVIDIA NIM Accelerated Adversarial Deep-Dive" in res["markdown_report"]
    assert res["nvidia_ledger_id"] in res["markdown_report"]


def test_note_extractor_agent_with_nvidia():
    """Verify NoteExtractorAgent delegates qualitative footnote queries to NVIDIA client."""
    from agents.note_extractor import NoteExtractorAgent
    agent = NoteExtractorAgent()
    res = agent.audit_footnote_with_nvidia(
        ticker="NVDA",
        footnote_text="Note 19: Customer A accounted for 22% of total consolidated net revenue.",
        focus_topic="Customer Concentration",
    )
    assert res["ticker"] == "NVDA"
    assert res["ledger_id"] is not None
    assert "22" in res["content"]


def test_nvidia_client_network_resilience_fallback(monkeypatch):
    """Verify that network exceptions trigger graceful fail-safe to deterministic output."""
    client = NvidiaNimClient(api_key="mock-key-for-test", offline_mode=False)

    def mock_call_error(*args, **kwargs):
        raise ConnectionError("Simulated network outage to api.nvidia.com")

    monkeypatch.setattr(client, "_call_nvidia_api", mock_call_error)
    ledger = ProvenanceLedger()

    res = client.chat_completion(
        messages=[{"role": "user", "content": "Adversarial stress-test for TSLA"}],
        ledger=ledger,
        ticker="TSLA",
    )

    assert res["offline_fallback"] is True
    assert "Adversarial Stress-Test Critique" in res["content"]
    assert res["ledger_id"] is not None

