# Dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装所需的Python包
RUN pip install --no-cache-dir requests telethon cryptg aiohttp FastTelethonhelper

# 运行脚本
CMD ["python", "app.py"]
