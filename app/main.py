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

app = FastAPI(title="Edu LLM API", version="1.2.0")

# ======== CORS 配置 ========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 前端 localhost:8081、网页都能访问
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======== 全局中间件：API Key 守卫 ========
@app.middleware("http")
async def guard_middleware(request: Request, call_next):
    await api_guard(request)
    return await call_next(request)

# ======== 路由注册 ========
app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])

# 健康检查（免认证）
@app.get("/v1/health")
def health():
    return {"status": "ok"}

# ======== 静态网页：/web ========
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/")
def root():
    return RedirectResponse(url="/web")

# ======== Swagger 加上 x-api-key ========
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description="Edu LLM API with API Key (x-api-key required)"
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
