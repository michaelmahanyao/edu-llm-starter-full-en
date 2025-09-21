# ===== builder（可选，便于后续扩展）=====
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100
WORKDIR /app
COPY requirements.txt ./
# 如果你使用了 constraints.txt，就把下一行改成：
# RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt
RUN pip install --no-cache-dir -r requirements.txt

# ===== runtime =====
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
# 拷贝依赖
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin/ /usr/local/bin/
# 拷贝代码
COPY . /app

# Render 会注入 PORT 环境变量，这里暴露一下方便本地调试
EXPOSE 8000

# 统一启动命令：让 Render/Heroku 等都能跑
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
