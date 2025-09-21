from __future__ import annotations
import os
import time
import requests
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"
PROVIDER_API_KEY: str = os.getenv("PROVIDER_API_KEY", "")
PROVIDER_BASE_URL: str = os.getenv("PROVIDER_BASE_URL", "https://api.openai.com/v1")
CHAT_MODEL: str = os.getenv("PROVIDER_CHAT_MODEL", "gpt-4o-mini")
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "60"))


# 请求/响应模型
class ChatMessage(BaseModel):
    role: str = Field(..., description="user / assistant / system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 512


class ChatResponse(BaseModel):
    content: str
    model: str
    elapsed_ms: int


@router.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(req: ChatRequest):
    """
    聊天补全 API：
    - DEMO_MODE: 返回固定 demo 文本
    - 真模式: 调用 PROVIDER_CHAT_MODEL 生成回复
    """
    t0 = time.time()

    if DEMO_MODE or not PROVIDER_API_KEY:
        return ChatResponse(
            content="[DEMO] Hello! This is a demo chat reply. Connect a real model to see dynamic answers.",
            model="demo-chat-model",
            elapsed_ms=int((time.time() - t0) * 1000),
        )

    url = f"{PROVIDER_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {PROVIDER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": CHAT_MODEL,
        "messages": [m.dict() for m in req.messages],
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=HTTP_TIMEOUT)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])

        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        return ChatResponse(
            content=content,
            model=CHAT_MODEL,
            elapsed_ms=int((time.time() - t0) * 1000),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat error: {e}")
