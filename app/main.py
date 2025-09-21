from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from .routers import solve, chat
from .security import api_guard
from fastapi.openapi.utils import get_openapi   # 👈 新增

app = FastAPI(title="Edu LLM API (Full EN + API Key)", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 API Key 中间件
@app.middleware("http")
async def guard_middleware(request: Request, call_next):
    await api_guard(request)
    return await call_next(request)

app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])

@app.get("/v1/health")
def health():
    return {"status": "ok", "message": "English version running"}

# 👇 新增：让 Swagger 显示 Authorize 按钮，支持 x-api-key
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
