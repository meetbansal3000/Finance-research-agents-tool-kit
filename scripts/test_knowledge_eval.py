"""
scripts/test_knowledge_eval.py - Upgrade 5 Knowledge Base Demonstration
Ingests one 10-K filing (Apple Inc. FY2025 10-K) and queries three distinct questions
with citations pointing to the document and page or section.
"""

import os
import sys

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.knowledge import LocalKnowledgeBase

def run_evaluation():
    kb = LocalKnowledgeBase()
    status = kb.status()
    print("=================================================================")
    print("📚 LOCAL KNOWLEDGE BASE (CHROMA) EVALUATION: APPLE FY2025 10-K")
    print("=================================================================")
    print(f"Collection: {status['collection_name']}")
    print(f"Indexed Chunks: {status['total_chunks']}")
    print(f"Storage Directory: {status['persist_dir']}\n")

    questions = [
        {
            "num": 1,
            "title": "Revenue & Product Breakdown",
            "prompt": "What was Apple's net sales breakdown by product and services in fiscal 2025?",
            "search_query": "net sales by category Products and Services Performance iPhone Services Mac iPad"
        },
        {
            "num": 2,
            "title": "Geopolitical & Supply Chain Risks",
            "prompt": "What specific risks does Apple disclose regarding Greater China and international manufacturing?",
            "search_query": "manufacturing outsourcing partners China mainland Greater China trade disputes political events"
        },
        {
            "num": 3,
            "title": "Capital Return & Share Repurchases",
            "prompt": "What were Apple's share repurchase activities, dividends, and capital return in fiscal 2025?",
            "search_query": "Common stock repurchased share repurchase program dividends declared per share"
        }
    ]

    for q in questions:
        print(f"-----------------------------------------------------------------")
        print(f"❓ Question {q['num']} [{q['title']}]:")
        print(f"   \"{q['prompt']}\"")
        print(f"-----------------------------------------------------------------")
        hits = kb.search(q["search_query"], ticker="AAPL", top_k=2)
        if not hits:
            print("   No matching passages found.\n")
            continue

        for i, hit in enumerate(hits, start=1):
            print(f"   [Citation #{i}] {hit['citation']}")
            print(f"   Relevance Distance: {hit['distance']:.4f}")
            # Format snippet cleanly
            snippet = hit['text']
            if len(snippet) > 350:
                snippet = snippet[:350] + "..."
            print(f"   Excerpt: \"{snippet}\"\n")

if __name__ == "__main__":
    run_evaluation()
