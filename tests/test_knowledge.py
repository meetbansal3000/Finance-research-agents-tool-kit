"""
tests/test_knowledge.py - Test Suite for Local Knowledge Base (Upgrade 5)
Tests:
1. Document ingestion and sensible chunking with preserved metadata.
2. Citation generation pointing to document and page/section.
3. Three evaluation questions on ingested Apple FY2025 10-K.
4. Verification of Standing Rule 12 across rulebooks.
"""

import os
import pytest
from tools.knowledge import LocalKnowledgeBase

@pytest.fixture(scope="module")
def kb():
    return LocalKnowledgeBase()

def test_knowledge_base_status_and_chunks(kb):
    status = kb.status()
    assert status["total_chunks"] > 0, "Knowledge base should have indexed chunks"
    assert "financial_research_library" in status["collection_name"]

def test_metadata_and_citations(kb):
    hits = kb.search("iPhone net sales", ticker="AAPL", top_k=1)
    assert len(hits) >= 1, "Should find results for iPhone sales"
    hit = hits[0]
    
    assert "citation" in hit
    citation = hit["citation"]
    assert citation.startswith("[Citation:")
    assert "AAPL" in citation
    assert "filing" in citation
    assert "AAPL_10K_FY2025.htm" in citation
    assert "Source:" in citation
    assert "Date:" in citation

def test_apple_10k_question_1_sales_breakdown(kb):
    """Q1: What were Apple's net sales breakdown by product and services in fiscal 2025?"""
    query = "net sales by category Products and Services Performance iPhone Services Mac iPad"
    hits = kb.search(query, ticker="AAPL", top_k=3)
    assert len(hits) >= 1

    combined_text = " ".join([h["text"] for h in hits])
    assert "209,586" in combined_text or "iPhone" in combined_text
    assert "Services" in combined_text
    assert "416,161" in combined_text or "Total net sales" in combined_text

def test_apple_10k_question_2_greater_china_risks(kb):
    """Q2: What specific risks does Apple disclose regarding Greater China and international manufacturing?"""
    query = "manufacturing outsourcing partners China mainland Greater China trade disputes political events"
    hits = kb.search(query, ticker="AAPL", top_k=3)
    assert len(hits) >= 1

    combined_text = " ".join([h["text"] for h in hits])
    assert "China" in combined_text
    assert "hardware products" in combined_text or "partners" in combined_text or "disputes" in combined_text

def test_apple_10k_question_3_capital_return_repurchases(kb):
    """Q3: What were Apple's share repurchase and capital return activities in fiscal 2025?"""
    query = "Common stock repurchased share repurchase program dividends declared per share"
    hits = kb.search(query, ticker="AAPL", top_k=3)
    assert len(hits) >= 1

    combined_text = " ".join([h["text"] for h in hits])
    assert "repurchased" in combined_text or "repurchase program" in combined_text or "Dividends" in combined_text

def test_rule_12_presence():
    """Verify that Rule 12 (Check local knowledge base before web) exists in playbooks."""
    root = os.path.dirname(os.path.dirname(__file__))
    playbook_path = os.path.join(root, "research_playbook_v2.md")
    rules_path = os.path.join(root, ".agents", "rules", "research_rules.md")

    with open(playbook_path, "r", encoding="utf-8") as f:
        playbook_text = f.read()
    assert "12. Check the local knowledge base" in playbook_text

    with open(rules_path, "r", encoding="utf-8") as f:
        rules_text = f.read()
    assert "12. **Knowledge Base Priority**" in rules_text
