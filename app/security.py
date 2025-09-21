import os, time
from fastapi import Request, HTTPException

API_KEY = os.getenv("API_KEY", "")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))  # requests per IP per minute

# Exempt paths (no auth)
_exempt_paths = {"/", "/v1/health", "/docs", "/openapi.json", "/redoc"}

# naive in-memory store (for demos; use Redis in production)
_request_log = {}

async def api_guard(request: Request):
    # 1) Allow CORS preflight
    if request.method == "OPTIONS":
        return

    # 2) Allow exempt paths
    if request.url.path in _exempt_paths:
        return

    # 3) API key check
    key = request.headers.get("x-api-key", "")
    if not API_KEY or key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing x-api-key")

    # 4) Simple per-IP rate limit
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0
    history = [t for t in _request_log.get(ip, []) if now - t < window]
    if len(history) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Too many requests, please slow down.")
    history.append(now)
    _request_log[ip] = history
