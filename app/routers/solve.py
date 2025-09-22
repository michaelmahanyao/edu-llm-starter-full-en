from __future__ import annotations

import os
import re
import json
import uuid
import time
import base64
from typing import List, Optional, Tuple, Dict, Any

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()

# =========================
# 环境变量 & 默认配置
# =========================
DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"

# 真实模型：建议使用 OpenAI
PROVIDER_API_KEY: str = os.getenv("PROVIDER_API_KEY", "")
PROVIDER_BASE_URL: str = os.getenv("PROVIDER_BASE_URL", "https://api.openai.com/v1")

# 视觉模型（图片 → 文本）
VISION_MODEL: str = os.getenv("PROVIDER_VISION_MODEL", "gpt-4o-mini")
# 文本模型（生成步骤/答案）
TEXT_MODEL: str = os.getenv("PROVIDER_TEXT_MODEL", "gpt-4o-mini")

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "60"))

# =========================
# Pydantic 模型
# =========================
class ProblemInput(BaseModel):
    text: Optional[str] = Field(default=None, description="题目文本，可留空，只传图片")
    image_url: Optional[str] = Field(default=None, description="data URL 或 https URL")
    grade_band: Optional[str] = Field(default=None, description="primary/middle/high 等")
    subject: Optional[str] = Field(default="math", description="学科，如 math/physics 等")
    knowledge_tags: List[str] = Field(default_factory=list)
    difficulty: Optional[str] = Field(default="medium")
    require_explanation: bool = Field(default=True)


class Solution(BaseModel):
    final_answer: Optional[str] = None


class PedagogyView(BaseModel):
    socratic_questions: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)


class NormalizedProblem(BaseModel):
    text: str
    latex: Optional[str] = None
    knowledge_tags: List[str] = Field(default_factory=list)


class ProblemOutput(BaseModel):
    problem_id: str
    normalized_problem: NormalizedProblem
    latex: Optional[str] = None
    knowledge_tags: List[str] = Field(default_factory=list)

    # 解题主体
    steps: List[str] = Field(default_factory=list)
    hints: List[str] = Field(default_factory=list)
    common_mistakes: List[str] = Field(default_factory=list)
    check: Optional[str] = None
    solution: Solution = Field(default_factory=Solution)
    pedagogy_view: PedagogyView = Field(default_factory=PedagogyView)


# =========================
# 工具：data URL 识别/解析
# =========================
_DATA_URL_RE = re.compile(r"^data:(?P<mime>[\w/+.-]+);base64,(?P<b64>.+)$", re.I)


def is_data_url(s: str) -> bool:
    return bool(_DATA_URL_RE.match(s or ""))


def decode_data_url(data_url: str) -> Tuple[str, bytes]:
    m = _DATA_URL_RE.match(data_url or "")
    if not m:
        raise ValueError("invalid data URL")
    mime = m.group("mime")
    b64 = m.group("b64")
    return mime, base64.b64decode(b64)


# =========================
# 调用模型：视觉 OCR（图片 → 文本）
# =========================
def ocr_extract_text_with_vision(image_url: str) -> str:
    if DEMO_MODE:
        return "[DEMO] OCR skipped: please connect a real vision model."

    if not PROVIDER_API_KEY:
        return "[WARN] PROVIDER_API_KEY not set — cannot OCR the image."

    url = f"{PROVIDER_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {PROVIDER_API_KEY}",
        "Content-Type": "application/json",
    }

    prompt = (
        "Extract ONLY the math/physics problem as clean plain text. "
        "No extra words, no commentary. If diagrams are essential, briefly describe."
    )

    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=HTTP_TIMEOUT)
        if resp.status_code != 200:
            return f"[OCR error] HTTP {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        return text or "[OCR] Empty result."
    except Exception as e:
        return f"[OCR exception] {e}"


# =========================
# 调用模型：文本模型完成“解题步骤/最终答案”生成
# =========================
SOLVE_SYS_PROMPT = (
    "You are an expert math tutor. Given a problem, produce a JSON object with keys:\n"
    "steps (array of strings; detailed step-by-step),\n"
    "final_answer (string; concise result only),\n"
    "hints (array), common_mistakes (array), check (string),\n"
    "and pedagogy_view with socratic_questions (array) and misconceptions (array).\n"
    "Return ONLY valid JSON, no extra text."
)


def call_text_model_to_solve(problem_text: str, difficulty: str = "medium") -> Dict[str, Any]:
    if DEMO_MODE or not PROVIDER_API_KEY:
        return {
            "steps": [
                "[DEMO] This is a demo explanation:",
                "1) Understand the question.",
                "2) Set up and transform equations.",
                "3) Verify the result.",
                "Final answer: x = 4",
            ],
            "final_answer": "see the end of the explanation",
            "hints": [
                "Read the problem carefully.",
                "Simplify step by step.",
                "Always check your answer.",
            ],
            "common_mistakes": [
                "Sign errors",
                "Arithmetic slips",
            ],
            "check": "Steps reviewed; conclusion consistent",
            "pedagogy_view": {
                "socratic_questions": [
                    "What does the problem ask for?",
                    "What operation can we apply to both sides first?",
                ],
                "misconceptions": [
                    "Confusing coefficients with exponents",
                ],
            },
        }

    url = f"{PROVIDER_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {PROVIDER_API_KEY}",
        "Content-Type": "application/json",
    }

    user_prompt = (
        f"Difficulty: {difficulty}\n"
        f"Problem:\n{problem_text}\n\n"
        "Respond in JSON only."
    )

    payload = {
        "model": TEXT_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SOLVE_SYS_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=HTTP_TIMEOUT)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"LLM error: {resp.text[:500]}")
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        out = json.loads(content)
        out.setdefault("steps", [])
        out.setdefault("final_answer", "")
        out.setdefault("hints", [])
        out.setdefault("common_mistakes", [])
        out.setdefault("check", "")
        out.setdefault("pedagogy_view", {"socratic_questions": [], "misconceptions": []})
        return out
    except Exception as e:
        return {
            "steps": ["[ERROR] text-model exception", str(e)],
            "final_answer": "",
            "hints": [],
            "common_mistakes": [],
            "check": "",
            "pedagogy_view": {"socratic_questions": [], "misconceptions": []},
        }


# =========================
# /solve 主路由（注意：这里不要再写 /v1）
# =========================
@router.post("/solve", response_model=ProblemOutput)
async def solve_problem(input: ProblemInput, request: Request):
    t0 = time.time()
    raw_text = (input.text or "").strip()
    image_url = (input.image_url or "").strip()
    difficulty = (input.difficulty or "medium").lower()

    extracted_text = ""
    if image_url:
        extracted_text = ocr_extract_text_with_vision(image_url)

    problem_text = raw_text
    if not problem_text and extracted_text:
        problem_text = extracted_text
    elif problem_text and extracted_text:
        problem_text = f"{problem_text}\n\n[OCR]\n{extracted_text}"

    if not problem_text:
        raise HTTPException(status_code=400, detail="No problem text. Provide text or a valid image_url.")

    solve_out = call_text_model_to_solve(problem_text, difficulty=difficulty)

    pid = f"prob_{uuid.uuid4().hex[:8]}"
    normalized = NormalizedProblem(
        text=problem_text,
        latex=None,
        knowledge_tags=input.knowledge_tags or [],
    )

    final = ProblemOutput(
        problem_id=pid,
        normalized_problem=normalized,
        latex=None,
        knowledge_tags=input.knowledge_tags or [],
        steps=list(solve_out.get("steps", [])),
        hints=list(solve_out.get("hints", [])),
        common_mistakes=list(solve_out.get("common_mistakes", [])),
        check=solve_out.get("check", None),
        solution=Solution(final_answer=solve_out.get("final_answer") or ""),
        pedagogy_view=PedagogyView(
            socratic_questions=list(
                (solve_out.get("pedagogy_view") or {}).get("socratic_questions", [])
            ),
            misconceptions=list(
                (solve_out.get("pedagogy_view") or {}).get("misconceptions", [])
            ),
        ),
    )

    _elapsed = round((time.time() - t0) * 1000)
    return final

