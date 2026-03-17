# 使用官方 Python 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# 先复制依赖文件，利用 Docker 层缓存
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（排除不必要的文件）
COPY app.py auth.py models.py ./
COPY utils/ ./utils/
COPY intelligent_farm.sql ./
COPY module_config.json ./

# 创建非 root 用户运行应用
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露应用端口
EXPOSE 8502

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8502/_stcore/health || exit 1

# 运行应用
CMD ["streamlit", "run", "app.py", "--server.port", "8502", "--server.address", "0.0.0.0"]
