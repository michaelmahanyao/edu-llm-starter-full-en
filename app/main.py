# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

from .routers import solve, chat
from .security import api_guard

app = FastAPI(title="Edu LLM API (Full EN + API Key)", version="1.2.0")

# ✅ 先加 CORS，保证它是最外层
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",             # 你的本地前端
        "https://edu-llm-starter.onrender.com",  # 如果有前端托管在这个域也可以加上
        "*",                                  # 调试期兜底（可去掉）
    ],
    allow_credentials=False,   # 调试期先关 credentials，更容易观察到 * 生效
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router,  prefix="/v1", tags=["chat"])

# 健康检查
@app.get("/v1/health")
def health():
    return {"status": "ok", "message": "English version running"}

# ✅ CORS 验证接口（方便你直接在浏览器 Console 里 fetch 测）
@app.get("/v1/cors-check")
def cors_check():
    return {"ok": True}

# 静态 /web
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WEB_DIR  = os.path.join(BASE_DIR, "web")
app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/")
def root():
    return RedirectResponse(url="/web")

# 你的 API Key & 限流中间件（在 CORS 之后加）
@app.middleware("http")
async def guard_middleware(request: Request, call_next):
    await api_guard(request)  # 里面已放行 OPTIONS /web /docs 等
    return await call_next(request)

# Swagger 顶部 Authorize（x-api-key）
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

# app/main.py
from fastapi.responses import JSONResponse
import logging, traceback

@app.exception_handler(Exception)
async def all_exception_handler(request, exc):
    logging.exception("UNHANDLED EXCEPTION on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": str(exc),                    # 直接把错误返回
        },
    )

