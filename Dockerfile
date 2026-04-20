# 国内可直连 Docker Hub 时可直接 `FROM python:3.11-slim`
# 不可直连时可以尝试以下任一镜像：
#   FROM docker.1ms.run/library/python:3.11-slim
#   FROM docker.xuanyuan.me/library/python:3.11-slim
#   FROM hub.atomgit.com/amd64/python:3.11-slim
FROM docker.1ms.run/library/python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_EXTRA_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST="mirrors.aliyun.com pypi.tuna.tsinghua.edu.cn"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip \
 && pip install -e .

COPY src ./src
COPY configs ./configs
COPY scripts ./scripts

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "aiops.main:app", "--host", "0.0.0.0", "--port", "8000"]
