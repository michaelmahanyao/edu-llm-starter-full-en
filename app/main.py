from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import solve, chat

app = FastAPI(title="Edu LLM API (Full EN)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(solve.router, prefix="/v1", tags=["solve"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])

@app.get("/v1/health")
def health():
    return {"status": "ok", "message": "English version running"}
