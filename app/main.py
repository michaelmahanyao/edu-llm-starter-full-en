# app/main.py
import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from .routers import solve, chat
from .security import api_guard

app = FastAPI(title="Edu LLM API (Full EN + API Key)", version="1.2.0")

# 1) 先加 CORS（放最外层，保证任何异常也带 CORS 头）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",               # 你的本地前端
        "https://edu-llm-starter.onrender.com",# 如果前端托管到这个域
        "*"                                    # 调试期兜底（生产可去掉）
    ],
    allow_credentials=False,                   # 调试为 False，更容易观察到 * 正常返回
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2) 业务路由（solve/chat）
app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router,  prefix="/v1", tags=["chat"])

# 3) 健康检查 + CORS 自检
@app.get("/v1/health")
def health():
    return {"status": "ok", "message": "English version running"}

@app.get("/v1/cors-check")
def cors_check():
    return {"ok": True}

# 4) 静态 /web（可选）
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WEB_DIR  = os.path.join(BASE_DIR, "web")
if os.path.isdir(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/")
def root():
    # 有 web/ 就跳 web，没有也无妨
    return RedirectResponse(url="/web" if os.path.isdir(WEB_DIR) else "/v1/health")

# 5) API Key & 限流中间件（在 CORS 之后）
@app.middleware("http")
async def guard_middleware(request: Request, call_next):
    await api_guard(request)        # 内部已放行 OPTIONS /web /docs /openapi.json 等
    return await call_next(request)

# 6) Swagger 顶部 Authorize（x-api-key）
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description="Edu LLM API with API Key auth (x-api-key)."
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "x-api-key",
    }
    schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi

# 7) 兜底异常处理（把错误直接返回，便于定位）
@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    logging.exception("UNHANDLED EXCEPTION on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc)},
    )

# 8) 调试接口：确认 header 里是否带上 x-api-key，env 是否有 API_KEY
@app.get("/v1/whoami")
async def whoami(req: Request):
    return {
        "x_api_key_header": req.headers.get("x-api-key"),
        "api_key_env_is_set": bool(os.getenv("API_KEY")),
    }

