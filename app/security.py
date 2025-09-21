import os, time
from fastapi import Request, HTTPException

API_KEY = os.getenv("API_KEY", "")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))  # requests per IP per minute

# 精确放行的路径
_EXEMPT_EXACT = {"/", "/v1/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}

# 前缀放行（整个子树都放行）
_EXEMPT_PREFIXES = ("/web", "/docs", "/static")  # /web/**、/docs/** 都放行

_request_log = {}

async def api_guard(request: Request):
    path = request.url.path

    # 1) 放行 CORS 预检
    if request.method == "OPTIONS":
        return

    # 2) 放行静态/文档路径（精确或前缀）
    if path in _EXEMPT_EXACT or any(path.startswith(p) for p in _EXEMPT_PREFIXES):
        return

    # 3) 校验 API Key（业务接口才需要）
    key = request.headers.get("x-api-key", "")
    if not API_KEY or key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing x-api-key")

    # 4) 简易限流（按 IP / 分钟）
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0
    history = [t for t in _request_log.get(ip, []) if now - t < window]
    if len(history) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Too many requests, please slow down.")
    history.append(now)
    _request_log[ip] = history
