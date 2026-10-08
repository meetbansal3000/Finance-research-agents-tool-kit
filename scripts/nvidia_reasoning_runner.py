"""
scripts/nvidia_reasoning_runner.py - NVIDIA NIM Reasoning Models Runner
Demonstrates live deep reasoning, multi-key failover, and streaming tokens across:
  - nvidia/nemotron-3-ultra-550b-a55b (550B flagship thinking model)
  - nvidia/nemotron-3.5-lightning-30b-a3b (30B lightning thinking model)
  - poolside/laguna-xs-2.1 (specialized comparison model)

All API keys are securely retrieved from the local untracked .env file.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure local workspace paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from tools.nvidia_client import NvidiaNimClient


def run_lightning_30b_limerick(client: NvidiaNimClient, stream: bool = True):
    print("=" * 70)
    print("[NVIDIA NIM] Running nvidia/nemotron-3.5-lightning-30b-a3b (Thinking Enabled)")
    print(f"Active Key: {client.get_masked_key()}")
    print("=" * 70)

    prompt = "Write a limerick about the wonders of GPU computing."
    messages = [{"role": "user", "content": prompt}]

    if stream:
        print("\n--- Reasoning & Generation Stream ---")
        try:
            for reasoning_chunk, content_chunk in client.stream_completion(
                messages=messages,
                model="nvidia/nemotron-3.5-lightning-30b-a3b",
                temperature=1.0,
                top_p=0.95,
                max_tokens=4096,
                enable_thinking=True,
                reasoning_budget=4096,
            ):
                if reasoning_chunk:
                    print(f"[THINKING: {reasoning_chunk}]", end="", flush=True)
                if content_chunk:
                    print(content_chunk, end="", flush=True)
            print("\n")
        except Exception as e:
            print(f"Streaming error: {e}. Executing non-streaming fallback...")
            res = client.chat_completion(
                messages=messages,
                model="nvidia/nemotron-3.5-lightning-30b-a3b",
                temperature=1.0,
                max_tokens=4096,
                enable_thinking=True,
            )
            print(res["content"])
    else:
        res = client.chat_completion(
            messages=messages,
            model="nvidia/nemotron-3.5-lightning-30b-a3b",
            temperature=1.0,
            max_tokens=4096,
            enable_thinking=True,
        )
        print(res["content"])


def run_laguna_comparison(client: NvidiaNimClient):
    print("=" * 70)
    print("[POOLSIDE] Running poolside/laguna-xs-2.1 (Comparison)")
    print(f"Active Key: {client.get_masked_key()}")
    print("=" * 70)

    prompt = "Which number is larger, 9.11 or 9.8?"
    messages = [{"role": "user", "content": prompt}]

    res = client.chat_completion(
        messages=messages,
        model="poolside/laguna-xs-2.1",
        temperature=1.0,
        top_p=0.95,
        max_tokens=4096,
        enable_thinking=False,
    )
    print(f"Prompt: {prompt}")
    print(f"Output: {res['content']}\n")


def run_ultra_550b_limerick(client: NvidiaNimClient, stream: bool = True):
    print("=" * 70)
    print("[NVIDIA NIM] Running nvidia/nemotron-3-ultra-550b-a55b (550B Flagship Reasoning)")
    print(f"Active Key: {client.get_masked_key()}")
    print("=" * 70)

    prompt = "Write a limerick about the wonders of GPU computing."
    messages = [{"role": "user", "content": prompt}]

    if stream:
        print("\n--- Reasoning & Generation Stream ---")
        try:
            for reasoning_chunk, content_chunk in client.stream_completion(
                messages=messages,
                model="nvidia/nemotron-3-ultra-550b-a55b",
                temperature=1.0,
                top_p=0.95,
                max_tokens=4096,
                enable_thinking=True,
            ):
                if reasoning_chunk:
                    print(f"[THINKING: {reasoning_chunk}]", end="", flush=True)
                if content_chunk:
                    print(content_chunk, end="", flush=True)
            print("\n")
        except Exception as e:
            print(f"Streaming error: {e}. Executing non-streaming fallback...")
            res = client.chat_completion(
                messages=messages,
                model="nvidia/nemotron-3-ultra-550b-a55b",
                temperature=1.0,
                max_tokens=4096,
                enable_thinking=True,
            )
            print(res["content"])
    else:
        res = client.chat_completion(
            messages=messages,
            model="nvidia/nemotron-3-ultra-550b-a55b",
            temperature=1.0,
            max_tokens=4096,
            enable_thinking=True,
        )
        print(res["content"])


def main():
    parser = argparse.ArgumentParser(description="NVIDIA NIM Reasoning Runner")
    parser.add_argument("--model", choices=["lightning", "laguna", "ultra", "all"], default="all", help="Model to run")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming tokens")
    args = parser.parse_args()

    client = NvidiaNimClient()
    print(f"Initialized NVIDIA NIM Client with {len(client.api_keys)} key(s) in pool.")

    if args.model in ("lightning", "all"):
        run_lightning_30b_limerick(client, stream=not args.no_stream)

    if args.model in ("laguna", "all"):
        run_laguna_comparison(client)

    if args.model in ("ultra", "all"):
        run_ultra_550b_limerick(client, stream=not args.no_stream)


if __name__ == "__main__":
    main()
