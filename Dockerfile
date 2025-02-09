# 使用官方 Python 基础镜像
FROM python:3.11

# 设置工作目录
WORKDIR /app

# 复制当前目录下的所有文件到工作目录
COPY . /app

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 暴露应用端口
EXPOSE 8502


# 运行应用
CMD ["streamlit", "run", "app.py", "--server.port", "8502"]
