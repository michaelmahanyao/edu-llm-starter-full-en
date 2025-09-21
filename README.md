# Edu LLM API — Full English Version

Endpoints:
- `POST /v1/solve` — solve a problem (text or image url) and return step-by-step explanation
- `POST /v1/chat/completions` — pedagogy-aware chat
- `GET /v1/health` — health check

Quick deploy on Render:
- Language: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env Vars:
  - `DEMO_MODE=true` (no key needed)
  - For real models: `DEMO_MODE=false`, `PROVIDER_API_KEY=sk-...`, `PROVIDER_BASE_URL=https://api.openai.com/v1`
  - Optional routing: `MODEL_EASY`, `MODEL_MEDIUM`, `MODEL_HARD`

Examples:
- `/v1/solve` body:
```json
{ "text": "Solve: 2x + 3 = 11", "difficulty": "easy" }
```
- `/v1/chat/completions` body:
```json
{ "messages": [{"role":"user","content":"Explain the Pythagorean theorem step by step."}], "pedagogy":"step_by_step" }
```
