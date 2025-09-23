# app/main.py
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import Request
import os

from .routers import solve, chat
from .security import api_guard

app = FastAPI(title="Edu LLM API (Full EN + API Key)", version="1.2.0")

# 1) CORS 一定要最外层，允许所有源、方法、头（含 x-api-key）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],              # 也可以用 allow_origin_regex=".*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# 2) 显式处理所有路径的 OPTIONS，返回 204（交给 CORS 中间件加头）
@app.options("/{path:path}")
async def any_options(path: str):
    return Response(status_code=204)

# 3) API Key 保护（记得先在 security.py 放行 OPTIONS，我们下面会给）
@app.middleware("http")
async def guard_middleware(request: Request, call_next):
    # 这里不要处理 CORS；只做鉴权+限流
    await api_guard(request)
    return await call_next(request)

# 业务路由
app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])

# 健康检查（免认证）
@app.get("/v1/health")
def health():
    return {"status": "ok", "message": "English version running"}

# ===== 静态网页 /web =====
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/")
def root():
    return RedirectResponse(url="/web")

# ===== Swagger 顶部加 Authorize (x-api-key) =====
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
