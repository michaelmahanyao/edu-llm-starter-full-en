# app/security.py
import os, time
from fastapi import Request, HTTPException

API_KEY = os.getenv("API_KEY", "")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))

_EXEMPT_EXACT = {
    "/",
    "/v1/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
}

_EXEMPT_PREFIXES = (
    "/web",
    "/docs",
    "/static",
)

_request_log = {}

async def api_guard(request: Request):
    path = request.url.path

    # 1) 必须放行 CORS 预检；否则浏览器拿不到 CORS 头
    if request.method == "OPTIONS":
        return

    # 2) 放行静态/文档等
    if (path in _EXEMPT_EXACT) or any(path.startswith(p) for p in _EXEMPT_PREFIXES):
        return

    # 3) 业务接口需要 x-api-key
    key = request.headers.get("x-api-key", "")
    if not API_KEY or key != API_KEY:
        # 401 也会带 CORS 头（由 CORSMiddleware 统一加），浏览器才看得到
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing x-api-key")

    # 4) 简单限流（按 IP / min）
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0
    history = [t for t in _request_log.get(ip, []) if now - t < window]
    if len(history) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Too many requests, please slow down.")
    history.append(now)
    _request_log[ip] = history
# app/security.py（节选）
_EXEMPT_EXACT = {
    "/",
    "/v1/health",
    "/v1/cors-check",    # ✅ 新增：CORS 自检接口无需 x-api-key
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
}
