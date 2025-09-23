# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
import os

from .routers import solve, chat
from .security import api_guard

app = FastAPI(title="Edu LLM API (Full EN + API Key)", version="1.2.2")

# ── 1) CORS 一定要先、而且要尽量“外层” ─────────────────────────────
# 说明：Starlette/FastAPI 中间件的顺序很重要。
# 这段放在最前面，以确保无论是预检（OPTIONS）还是异常响应，都能附带 CORS 头。
app.add_middleware(
    CORSMiddleware,
    # 开发阶段最省心：全放开（上线后建议改成你的域名列表）
    allow_origins=["*"],
    allow_credentials=False,           # 我们用 header 鉴权，不用 cookie
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# ── 2) 全局中间件：放行 OPTIONS、健康检查、文档、静态页 ────────────────
# 如果不放行，预检和静态页面会被挡住，浏览器看不到 CORS 头。
@app.middleware("http")
async def guard_middleware(request: Request, call_next):
    path = request.url.path

    # 2.1 预检直接 204 返回，让 CORS 中间件加头
    if request.method == "OPTIONS":
        return Response(status_code=204)

    # 2.2 一些无需鉴权的路径（首页、静态页、健康检查、OpenAPI/Docs）
    if (
        path == "/" or
        path.startswith("/web") or
        path in {"/v1/health", "/docs", "/openapi.json", "/redoc"}
    ):
        return await call_next(request)

    # 2.3 其它路径才执行 API Key 校验
    await api_guard(request)
    return await call_next(request)

# 业务路由
app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])

# 健康检查（免认证）
@app.get("/v1/health")
def health():
    return {"status": "ok", "message": "English version running"}

# 静态网页：/web
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/")
def root():
    return RedirectResponse(url="/web")

# 让 Swagger 顶部有 Authorize（x-api-key）
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description="Edu LLM API with API Key auth (x-api-key).",
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
