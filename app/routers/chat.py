from __future__ import annotations

import os
import time
import uuid
from typing import List, Optional, Dict, Any

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# =========================
# 环境变量 & 默认配置
# =========================
DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"

# 真实模型：建议使用 OpenAI
PROVIDER_API_KEY: str = os.getenv("PROVIDER_API_KEY", "")
PROVIDER_BASE_URL: str = os.getenv("PROVIDER_BASE_URL", "https://api.openai.com/v1")

# 默认文本模型（可被请求体覆盖）
TEXT_MODEL: str = os.getenv("PROVIDER_TEXT_MODEL", "gpt-4o-mini")

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "60"))


# =========================
# Pydantic 模型（对齐 OpenAI Chat Completions 结构）
# =========================
class ChatMessage(BaseModel):
    role: str = Field(description="system/user/assistant")
    content: str


class ChatRequest(BaseModel):
    model: Optional[str] = Field(default=None, description="使用的模型，不传则用服务端默认")
    messages: List[ChatMessage]
    temperature: float = 0.7
    top_p: float = 1.0
    stream: bool = False  # 这里只实现非流式，设置 True 也按非流式处理
    extra: Dict[str, Any] = Field(default_factory=dict, description="透传字段（可选）")


class ChoiceMessage(BaseModel):
    role: str
    content: str


class ChatChoice(BaseModel):
    index: int
    message: ChoiceMessage
    finish_reason: str = "stop"


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]


# =========================
# DEMO 响应（无 KEY 可用时）
# =========================
def demo_completion(messages: List[ChatMessage], model: str) -> ChatResponse:
    user_last = ""
    for m in reversed(messages):
        if m.role == "user":
            user_last = m.content
            break

    content = (
        "[DEMO MODE]\n"
        "我是一个示例聊天接口，没有连接真实模型。\n\n"
        "你刚才的最后一句话是：\n"
        f"{user_last or '(未发现 user 消息)'}\n\n"
        "提示：在 Render 环境变量中设置 PROVIDER_API_KEY 后即可接入真实模型。"
    )

    return ChatResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:10]}",
        created=int(time.time()),
        model=model,
        choices=[
            ChatChoice(
                index=0,
                message=ChoiceMessage(role="assistant", content=content),
                finish_reason="stop",
            )
        ],
    )


# =========================
# 转发到 OpenAI 兼容的 Chat Completions
# =========================
def forward_to_provider(req: ChatRequest) -> ChatResponse:
    if not PROVIDER_API_KEY:
        # 没有 KEY，则走 demo
        return demo_completion(req.messages, req.model or TEXT_MODEL)

    url = f"{PROVIDER_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {PROVIDER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": req.model or TEXT_MODEL,
        "temperature": req.temperature,
        "top_p": req.top_p,
        "messages": [m.model_dump() for m in req.messages],
        # 不做流式（stream=false）
        "stream": False,
    }

    # 透传额外字段（可选）
    if req.extra:
        payload.update(req.extra)

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=HTTP_TIMEOUT)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        data = resp.json()
        # 仅取第一个 choice
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = msg.get("content") or ""

        return ChatResponse(
            id=data.get("id") or f"chatcmpl-{uuid.uuid4().hex[:10]}",
            created=data.get("created") or int(time.time()),
            model=data.get("model") or (req.model or TEXT_MODEL),
            choices=[
                ChatChoice(
                    index=0,
                    message=ChoiceMessage(
                        role=msg.get("role") or "assistant",
                        content=content,
                    ),
                    finish_reason=choice.get("finish_reason") or "stop",
                )
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        # 回落：返回一段错误说明，但保持 OpenAI 风格
        return ChatResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:10]}",
            created=int(time.time()),
            model=req.model or TEXT_MODEL,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChoiceMessage(
                        role="assistant",
                        content=f"[ERROR] provider exception: {e}",
                    ),
                    finish_reason="stop",
                )
            ],
        )


# =========================
# 路由：/chat/completions（⚠️不要加 /v1）
# =========================
@router.post("/chat/completions", response_model=ChatResponse)
def chat_completions(req: ChatRequest) -> ChatResponse:
    """
    OpenAI 兼容的 Chat Completions。
    - 在 DEMO_MODE 或没有 PROVIDER_API_KEY 的情况下返回示例答案；
    - 否则转发到 PROVIDER_BASE_URL 的 /chat/completions。
    """
    model = req.model or TEXT_MODEL

    # DEMO: 直接返回
    if DEMO_MODE and not PROVIDER_API_KEY:
        return demo_completion(req.messages, model)

    # 真实：转发给供应商
    return forward_to_provider(req)

