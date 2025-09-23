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

# 先注册业务路由
app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router,  prefix="/v1", tags=["chat"])

# 健康检查等无需认证
@app.get("/v1/health")
def health():
    return {"status": "ok", "message": "English version running"}

# 静态 /web
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WEB_DIR  = os.path.join(BASE_DIR, "web")
app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/")
def root():
    return RedirectResponse(url="/web")

# 你的 API Key & 限流中间件（放在内层）
@app.middleware("http")
async def guard_middleware(request: Request, call_next):
    await api_guard(request)  # 里面已经放行 OPTIONS /web /docs 等
    return await call_next(request)

# ⚠️ 最后再加 CORS（包在最外层，确保异常响应也带 CORS 头）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
