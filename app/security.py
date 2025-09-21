# app/security.py
import os, time
from fastapi import Request, HTTPException

API_KEY = os.getenv("API_KEY", "")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))

# 补充免认证路径
_exempt_paths = {"/", "/v1/health", "/docs", "/openapi.json", "/redoc"}

_request_log = {}

async def api_guard(request: Request):
    # 1) 放行 CORS 预检请求
    if request.method == "OPTIONS":
        return

    # 2) 放行免认证路径
    if request.url.path in _exempt_paths:
        return

    # 3) 校验 API Key
    key = request.headers.get("x-api-key", "")
    if not API_KEY or key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing x-api-key")

    # 4) 简单限流
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0
    history = [t for t in _request_log.get(ip, []) if now - t < window]
    if len(history) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Too many requests, please slow down.")
    history.append(now)
    _request_log[ip] = history
