# 基础镜像：小而稳定
FROM python:3.11-slim

# 基本环境
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先只拷贝 requirements.txt，便于缓存
COPY requirements.txt /app/

# 升级 pip 并安装依赖
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 再拷贝剩余代码
COPY . /app

# Render 会注入 $PORT，这里使用它
EXPOSE 10000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
