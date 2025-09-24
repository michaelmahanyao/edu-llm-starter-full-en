# app/security.py
import os, time
from fastapi import Request, HTTPException

API_KEY = os.getenv("API_KEY", "")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))  # req/min per IP

# 精确放行：这些路径不需要 x-api-key
_EXEMPT_EXACT = {
    "/", "/v1/health", "/v1/cors-check",
    "/docs", "/openapi.json", "/redoc", "/favicon.ico",
}

# 前缀放行：整棵子树不需要 x-api-key
_EXEMPT_PREFIXES = ("/web", "/docs", "/static")

# 内存限流
_request_log = {}

async def api_guard(request: Request):
    path = request.url.path

    # 1) 放行 CORS 预检
    if request.method == "OPTIONS":
        return

    # 2) 放行白名单路径
    if (path in _EXEMPT_EXACT) or any(path.startswith(p) for p in _EXEMPT_PREFIXES):
        return

    # 3) 业务接口：校验 x-api-key
    key = request.headers.get("x-api-key", "")
    if not API_KEY or key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing x-api-key")

    # 4) 限流（按 IP / 60s 窗口）
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    history = [t for t in _request_log.get(ip, []) if now - t < 60.0]
    if len(history) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Too many requests, please slow down.")
    history.append(now)
    _request_log[ip] = history
