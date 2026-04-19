# AIOps-Agent

知识库 + 运维多 Agent 协作系统。技术栈：Python + RAG + LangGraph + Kafka + Neo4j + Milvus + Redis Stack。

## 快速开始

### 1. 启动基础设施（Docker）

```bash
# 一键启动：Kafka / Redis-Stack / Milvus / Neo4j
bash scripts/setup.sh up

# 查看状态
docker compose ps

# 停止
bash scripts/setup.sh down
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 LLM API Key
```

### 3. 本地安装依赖

```bash
pip install -e ".[dev]"
```

### 4. 初始化数据

```bash
# Neo4j 拓扑
python scripts/init_neo4j.py

# Milvus collection
python scripts/init_milvus.py

# 写入样例知识
python scripts/seed_knowledge.py
```

### 5. 启动服务

```bash
# 方式 A：直接本地
uvicorn aiops.main:app --reload --port 8000

# 方式 B：完整 compose（含 app 容器）
docker compose up -d
```

### 6. 跑 Demo

```bash
# 问答 Demo
python examples/chat_demo.py

# 告警 -> 根因 -> 自愈 Demo
python examples/alert_demo.py
```

## 目录结构

见 `SPEC.md` 第 3 节。

## 测试

```bash
pytest tests/unit -v
pytest tests/integration -v  # 需要 compose 已启动
```

## 评估

```bash
python -m aiops.eval.ragas_runner --dataset data/eval.jsonl
```
