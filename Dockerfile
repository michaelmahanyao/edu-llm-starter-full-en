FROM python:3.11-slim

# 让 logs 立刻刷新 & 避免写出 .pyc
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ONLY_BINARY=:all:

WORKDIR /app

# 先拷 requirements 再安装，最大化缓存命中；prefer-binary 避免源码构建
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# 再拷贝其余代码
COPY . /app

# Render 会注入 $PORT，这里绑定 0.0.0.0:$PORT
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
