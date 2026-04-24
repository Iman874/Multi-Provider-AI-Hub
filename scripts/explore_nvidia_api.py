"""
Exploratory test script for NVIDIA NIM API.

Run: python scripts/test_nvidia_api.py

Tests:
1. List models (GET /v1/models)
2. Chat completion (POST /v1/chat/completions)
3. Streaming (POST /v1/chat/completions stream=true)
4. Embedding (POST /v1/embeddings)
"""

import httpx
import json
import os

BASE_URL = "https://integrate.api.nvidia.com/v1"
API_KEY = os.getenv("NVIDIA_API_KEY", "")

if not API_KEY:
    print("ERROR: Set NVIDIA_API_KEY env variable first")
    print("  PowerShell: $env:NVIDIA_API_KEY='nvapi-...'")
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def test_list_models():
    """Test 1: GET /v1/models — List available models."""
    print("\n" + "=" * 60)
    print("TEST 1: List Models (GET /v1/models)")
    print("=" * 60)

    resp = httpx.get(f"{BASE_URL}/models", headers=HEADERS, timeout=30)
    print(f"Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        models = data.get("data", [])
        print(f"Total models: {len(models)}")
        # Show first 10
        for m in models[:10]:
            print(f"  - {m.get('id', 'unknown')}")
        if len(models) > 10:
            print(f"  ... and {len(models) - 10} more")
    else:
        print(f"Error: {resp.text[:300]}")


def test_chat_completion():
    """Test 2: POST /v1/chat/completions — Non-streaming."""
    print("\n" + "=" * 60)
    print("TEST 2: Chat Completion (non-streaming)")
    print("=" * 60)

    payload = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [
            {"role": "user", "content": "Say hello in 1 sentence."}
        ],
        "max_tokens": 50,
        "temperature": 0.5,
    }

    resp = httpx.post(
        f"{BASE_URL}/chat/completions",
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    print(f"Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        print(f"Model: {data.get('model')}")
        print(f"Content: {data['choices'][0]['message']['content']}")
        print(f"Usage: {data.get('usage')}")
        print(f"\nFull response structure:")
        print(json.dumps(data, indent=2)[:500])
    else:
        print(f"Error: {resp.text[:300]}")


def test_streaming():
    """Test 3: POST /v1/chat/completions — Streaming (SSE)."""
    print("\n" + "=" * 60)
    print("TEST 3: Chat Completion (streaming)")
    print("=" * 60)

    payload = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [
            {"role": "user", "content": "Count from 1 to 5."}
        ],
        "max_tokens": 50,
        "stream": True,
    }

    print("Tokens: ", end="", flush=True)
    with httpx.stream(
        "POST",
        f"{BASE_URL}/chat/completions",
        headers=HEADERS,
        json=payload,
        timeout=60,
    ) as resp:
        print(f"[Status: {resp.status_code}]")
        if resp.status_code != 200:
            print(f"Error: {resp.read().decode()[:300]}")
            return

        for line in resp.iter_lines():
            if not line.strip():
                continue
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    print("\n[DONE]")
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        print(token, end="", flush=True)
                except json.JSONDecodeError:
                    pass
    print()


def test_embedding():
    """Test 4: POST /v1/embeddings."""
    print("\n" + "=" * 60)
    print("TEST 4: Embedding")
    print("=" * 60)

    payload = {
        "model": "nvidia/nv-embedqa-e5-v5",
        "input": "Machine learning is fascinating",
    }

    resp = httpx.post(
        f"{BASE_URL}/embeddings",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
    print(f"Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        emb = data["data"][0]["embedding"]
        print(f"Model: {data.get('model')}")
        print(f"Embedding dim: {len(emb)}")
        print(f"First 5 values: {emb[:5]}")
        print(f"Usage: {data.get('usage')}")
    else:
        print(f"Error: {resp.text[:300]}")
        print("\nNote: If model not found, try other models from NVIDIA catalog.")


if __name__ == "__main__":
    print(f"NVIDIA NIM API Explorer")
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY[:12]}...{API_KEY[-4:]}")

    test_list_models()
    test_chat_completion()
    test_streaming()
    test_embedding()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
