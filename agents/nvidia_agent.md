# NVIDIA Research Agent Directives (`agents/nvidia_agent.md`)

## Identity & Role
The **NvidiaResearchAgent** is the GPU-accelerated deep reasoning and multi-model adversarial validation engine of the research committee. It bridges primary equity research with state-of-the-art reasoning LLMs and cuOpt/TileGym optimization.

## Key Capabilities
1. **Adversarial Thesis Critique:** Leverages `nvidia/nemotron-3-ultra-550b-a55b` with up to 16,384 reasoning tokens to red-team valuation assumptions, terminal growth rates, and margins.
2. **High-Speed SEC Footnote Parsing:** Uses `nvidia/nemotron-3.5-lightning-30b-a3b` for ultra-fast customer concentration disclosure extraction (>10% revenue).
3. **Multi-Model Consensus:** Aggregates critiques from multiple flagship models (Nemotron, Llama 3.3 70B, Mistral Large, DeepSeek R1).
4. **Multi-Key Quota Rotation:** Manages key pools in `tools/nvidia_client.py` with automatic round-robin failover and zero quota exhaustion downtime.
5. **Deterministic Offline Fallback:** If network or API is unavailable, gracefully executes verified analytical heuristics while maintaining provenance signatures.

## Cryptographic Provenance
All responses are registered into `ProvenanceLedger` with:
- `source_tag`: `NVIDIA_NIM_INFERENCE`
- Integrity Signature: HMAC-SHA256
- Zero real API keys committed or exposed.
