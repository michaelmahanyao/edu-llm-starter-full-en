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

app = FastAPI(title="Edu LLM API (Full EN + API Key)", version="1.2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局中间件：API Key + 简易限流（security.py 已放行 OPTIONS、/、/docs 等）
@app.middleware("http")
async def guard_middleware(request: Request, call_next):
    await api_guard(request)
    return await call_next(request)

# 业务路由
app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])

# 健康检查（免认证）
@app.get("/v1/health")
def health():
    return {"status": "ok", "message": "English version running"}

# ======== 静态网页：/web ========
# 计算项目根目录（app/ 的上一级），确保能找到根目录下的 web/
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

# 挂载静态资源；html=True 让 /web 自动返回 web/index.html
app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

# 根路径跳转到 /web（如果想跳到 Swagger，改成 '/docs'）
@app.get("/")
def root():
    return RedirectResponse(url="/web")

# ======== 让 Swagger 顶部有 Authorize（x-api-key） ========
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
