# app/security.py
import os, time
from fastapi import Request, HTTPException

API_KEY = os.getenv("API_KEY", "")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))  # req/min per IP

# 精确放行：这些路径不需要 x-api-key
_EXEMPT_EXACT = {
    "/",                 # 根
    "/v1/health",        # 健康检查
    "/v1/cors-check",    # ✅ CORS 自检
    "/docs",             # Swagger UI
    "/openapi.json",     # OpenAPI
    "/redoc",
    "/favicon.ico",
}

# 前缀放行：整棵子树不需要 x-api-key
_EXEMPT_PREFIXES = (
    "/web",              # 静态网页
    "/docs",             # Swagger 静态资源
    "/static",
)

# 简易限流：内存版
_request_log = {}

async def api_guard(request: Request):
    path = request.url.path

    # 1) 必须放行 CORS 预检（OPTIONS），否则浏览器拿不到 CORS 头
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
    window = 60.0
    history = [t for t in _request_log.get(ip, []) if now - t < window]
    if len(history) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Too many requests, please slow down.")
    history.append(now)
    _request_log[ip] = history
