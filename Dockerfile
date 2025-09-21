FROM python:3.11-slim

# 避免写入 .pyc 文件、输出缓存
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先拷贝 requirements.txt 并安装依赖
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 再拷贝剩余代码
COPY . /app

# Render 会自动分配端口，用 $PORT
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
