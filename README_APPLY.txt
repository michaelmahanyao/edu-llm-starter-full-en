Security add-ons for Edu LLM API (Full EN)
==========================================

Files included:
- app/security.py  -> API key check + simple per-IP rate limiter
- app/main.py      -> wired the guard middleware (exempts /v1/health, /docs, /openapi.json)

How to apply:
1) Copy both files into your deployed project (overwrite app/main.py).
2) On Render, add environment variables:
   - API_KEY=your_super_secret_key
   - RATE_LIMIT_PER_MIN=60    # optional, default 60
3) Redeploy. All endpoints except /v1/health, /docs, /openapi.json now require the header:
   x-api-key: your_super_secret_key

Test with curl:
curl -X POST https://<your-app>.onrender.com/v1/solve \
  -H 'x-api-key: your_super_secret_key' -H 'Content-Type: application/json' \
  -d '{"text":"Solve: 2x + 3 = 11","difficulty":"easy"}'
