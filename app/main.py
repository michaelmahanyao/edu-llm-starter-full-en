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

app = FastAPI(title="Edu LLM API", version="1.2.2")

# ① CORS —— 放最前面
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 开发阶段先放开；上线时改成你的域名
    allow_credentials=False,  # 我们用 header 携带 x-api-key，不用 cookie
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# ② 全局中间件（先放行预检和静态/文档，再做 API Key 守卫）
@app.middleware("http")
async def guard_middleware(request: Request, call_next):
    path = request.url.path
    # 预检请求直接 204，保证浏览器顺利拿到 CORS 头
    if request.method == "OPTIONS":
        return Response(status_code=204)
    # 静态 & 文档 & 健康检查放行
    if path == "/" or path.startswith("/web") or path in {"/v1/health", "/docs", "/openapi.json", "/redoc"}:
        return await call_next(request)
    # 其余业务接口才做 Key 校验与限流（security.py 里已实现）
    await api_guard(request)
    return await call_next(request)

# ③ 业务路由
app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])

# ④ 健康检查
@app.get("/v1/health")
def health():
    return {"status": "ok"}

# ⑤ 静态站点 /web
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/")
def root():
    return RedirectResponse(url="/web")

# ⑥ Swagger 顶部挂 x-api-key
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description="Edu LLM API with API Key (x-api-key required).",
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
