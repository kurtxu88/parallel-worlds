# Parallel Worlds

Parallel Worlds 是一个开源的 AI 互动叙事项目，技术栈为 Vue、FastAPI、Neo4j OSS 和 Postgres。

当前开源首发版只保留核心闭环：

- 创建世界种子
- 由后台 worker 异步生成世界
- 进入世界并进行流式互动
- 从事件历史中恢复之前的游玩过程
- 为访客身份保存语言和主题偏好

这个仓库不包含之前私有产品仓的历史记录，而是一个全新的公开代码库。

## 技术栈

- `apps/web`：Vue 3 + Vite
- `apps/api`：FastAPI 接口与互动游玩入口
- `workers/story-generator`：异步世界生成 worker
- `db/postgres`：故事、事件、设置等关系型数据
- `db/neo4j`：生成世界图数据的图数据库说明
- `docker-compose.yml`：本地开发栈

## 快速开始

1. 复制环境变量模板。

```bash
cp .env.example .env
```

2. 在 `.env` 中填写 `OPENAI_API_KEY`。

3. 启动本地栈。

```bash
docker compose up --build
```

4. 浏览器打开 [http://localhost:5173](http://localhost:5173)。

5. API 健康检查地址为 [http://localhost:8000/api/health](http://localhost:8000/api/health)。

## 访客模式

开源版默认启用访客模式：

- 不使用 Supabase
- 不依赖托管认证
- 没有邮箱注册
- 没有邀请码系统

前端会先请求 `POST /api/session/guest`，把返回的 `guest_user_id` 保存到本地，再通过 `X-User-Id` 请求头访问业务 API。

## 环境变量

世界生成所需：

- `OPENAI_API_KEY`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`

故事、事件、设置存储所需：

- `DATABASE_URL`

前端：

- `VITE_API_BASE_URL`

本地默认值请查看 `.env.example`。

## 目录结构

```text
parallel-worlds/
  apps/
    api/
    web/
  workers/
    story-generator/
  db/
    postgres/
    neo4j/
  docs/
  examples/
  deploy/
    optional/
```

## v1 范围

已包含：

- 访客会话
- 我的世界列表
- 异步生成 worker
- 流式互动游玩
- 历史恢复
- 语言/主题设置

暂不包含：

- 公开世界市场
- 邀请机制
- 邮箱密码登录
- 默认托管部署配置

## 单独开发

仅启动前端：

```bash
cd apps/web
npm install
npm run dev
```

仅启动 API：

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

仅启动 worker：

```bash
cd workers/story-generator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python worker.py
```

## 文档

- [架构说明](./docs/architecture.md)
- [英文 README](./README.md)
- [贡献指南](./CONTRIBUTING.md)
- [安全策略](./SECURITY.md)
