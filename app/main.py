from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles            # ⬅️ 新增：挂静态目录
from fastapi.responses import RedirectResponse         # ⬅️ 新增：根路径跳转
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

# 👉 挂载静态网页到 /web
app.mount("/web", StaticFiles(directory="web", html=True), name="web")

# 👉 根路径跳到 /web（若只想跳到 /docs，把 '/web' 改成 '/docs'）
@app.get("/")
def root():
    return RedirectResponse(url="/web")

# 让 Swagger 顶部出现 Authorize（x-api-key）
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
        "name": "x-api-key"
    }
    schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi
