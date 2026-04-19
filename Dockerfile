FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

COPY src ./src
COPY configs ./configs
COPY scripts ./scripts

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "aiops.main:app", "--host", "0.0.0.0", "--port", "8000"]
