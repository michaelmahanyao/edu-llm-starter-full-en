import os, httpx, time

PROVIDER_API_KEY = os.getenv("PROVIDER_API_KEY", "")
PROVIDER_BASE_URL = os.getenv("PROVIDER_BASE_URL", "https://api.openai.com/v1")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

async def chat_completion(messages, model: str, temperature: float=0.2, max_tokens: int=512):
    if DEMO_MODE or not PROVIDER_API_KEY:
        # Deterministic mock for demo/testing
        content = "[DEMO] This is a demo explanation:\n1) Understand the question\n2) Set up and transform equations\n3) Verify the result\nFinal answer: x = 4"
        return {
            "id": f"demo-{int(time.time())}",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
    headers = {"Authorization": f"Bearer {PROVIDER_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{PROVIDER_BASE_URL}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()
