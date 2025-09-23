# app/main.py  —— 完整可用版
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

from .routers import solve, chat
from .security import api_guard

app = FastAPI(title="Edu LLM API (Full EN + API Key)", version="1.2.1")

# ======== CORS 配置 ========
# 开发环境允许所有来源，生产环境可以写成 ["https://你的域名.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 开发环境先放开
    allow_credentials=False,   # 用 header 鉴权，不需要 cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======== 全局中间件：API Key + 简易限流 ========
@app.middleware("http")
async def guard_middleware(request: Request, call_next):
    await api_guard(request)
    return await call_next(request)

# ======== 业务路由 ========
app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])

# ======== 健康检查（免认证） ========
@app.get("/v1/health")
def health():
    return {"status": "ok", "message": "English version running"}

# ======== 静态网页：/web ========
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/")
def root():
    return RedirectResponse(url="/web")

# ======== Swagger 加上 Authorize（x-api-key） ========
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
