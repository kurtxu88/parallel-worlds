# Parallel Worlds

[![CI](https://github.com/kurtxu88/parallel-worlds/actions/workflows/ci.yml/badge.svg)](https://github.com/kurtxu88/parallel-worlds/actions/workflows/ci.yml)
[![Release Drafter](https://github.com/kurtxu88/parallel-worlds/actions/workflows/release-drafter.yml/badge.svg)](https://github.com/kurtxu88/parallel-worlds/actions/workflows/release-drafter.yml)
[![Release](https://github.com/kurtxu88/parallel-worlds/actions/workflows/release.yml/badge.svg)](https://github.com/kurtxu88/parallel-worlds/actions/workflows/release.yml)
[![GitHub stars](https://img.shields.io/github/stars/kurtxu88/parallel-worlds?style=social)](https://github.com/kurtxu88/parallel-worlds/stargazers)

![Parallel Worlds social card](./apps/web/public/social-card.svg)

Parallel Worlds 是一个开源 AI 互动叙事项目，目标是把简短设定变成“可进入、可游玩、可持续扩展”的世界。

当前版本线：`v0.1.0`

项目使用 Vue、FastAPI、Neo4j OSS 和 Postgres 来支撑这条核心闭环：

- 创建世界种子
- 由后台 worker 异步生成世界
- 进入世界并进行流式互动
- 从事件历史中恢复之前的游玩过程
- 为访客身份保存语言和主题偏好

这个仓库不包含之前私有产品仓的历史记录，而是一个全新的公开代码库，会以公开方式持续迭代。

## 为什么要做这个项目

很多 AI 叙事 Demo 停留在“一次性生成文本”的层面。Parallel Worlds 想做的是让世界本身继续存在并可反复进入：

- Postgres 保存用户、故事、设置和事件历史
- Neo4j 保存游玩时使用的世界图结构
- API 与 worker 分离，便于分别演进生成与游玩逻辑
- 访客模式让开源版更容易在本地跑起来

如果你关心开源故事引擎、图结构叙事系统，或者想参与一个真正可 Hack 的小型全栈 AI 项目，这个仓库就是为你准备的。

## 项目状态

Parallel Worlds 目前处于公开早期阶段。

- 当前版本是聚焦核心闭环的 v1
- 路线图保持小步可交付
- 接下来的改进会优先提升可运行性、可演示性和可扩展性

当前方向请查看 [路线图](./docs/roadmap.zh-CN.md)。

## 技术栈

- `apps/web`：Vue 3 + Vite
- `apps/api`：FastAPI 接口与互动游玩入口
- `workers/story-generator`：异步世界生成 worker
- `db/postgres`：故事、事件、设置等关系型数据
- `db/neo4j`：生成世界图数据的图数据库说明
- `docker-compose.yml`：本地开发栈

## 当前范围

已包含：

- 访客会话
- 我的世界列表
- 异步生成 worker
- 流式互动游玩
- 历史恢复
- 语言/主题设置
- 单个世界的可选公开分享页

暂不包含：

- 公开世界市场
- 邀请机制
- 邮箱密码登录
- 默认托管部署配置

## 快速开始

前置要求：

- Docker
- 一个可用的 `OPENAI_API_KEY`

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

`.env.example` 默认已经按 Docker Compose 场景配置好了。

## 快速体验示例

可以先用下面这个种子跑通第一轮体验：

```json
{
  "user_input": "一位住在被海水吞没之月上的档案管理员，不断发现记录着“尚未发生的战争”的卷宗。",
  "gender_preference": "female",
  "culture_language": "zh-CN"
}
```

也可以直接分享带预填种子的链接，比如 `/create?seed=drowned-moon`。
如果在创建时开启分享，还可以把世界发布到 `/share/<story-id>`。

## 访客模式

开源版默认启用访客模式：

- 不使用 Supabase
- 不依赖托管认证
- 没有邮箱注册
- 没有邀请码系统

前端会先请求 `POST /api/session/guest`，把返回的 `guest_user_id` 保存到本地，再通过 `X-User-Id` 请求头访问业务 API。
公开世界页是按故事单独开启的可选能力，不会默认公开所有内容。

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
- `VITE_PUBLIC_SITE_URL`，用于生产环境下的 canonical 和社交预览链接

本地默认值请查看 `.env.example`。

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
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://parallel_worlds:parallel_worlds@localhost:5432/parallel_worlds
export NEO4J_URI=bolt://localhost:7687
uvicorn main:app --reload
```

仅启动 worker：

```bash
cd workers/story-generator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://parallel_worlds:parallel_worlds@localhost:5432/parallel_worlds
export NEO4J_URI=bolt://localhost:7687
python3 worker.py
```

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

## 文档

- [架构说明](./docs/architecture.md)
- [路线图](./docs/roadmap.zh-CN.md)
- [增长 Playbook](./docs/growth-playbook.zh-CN.md)
- [Demo 脚本](./docs/demo-script.zh-CN.md)
- [发布清单](./docs/launch-checklist.zh-CN.md)
- [发布流程](./docs/release-process.zh-CN.md)
- [英文 README](./README.md)
- [中文贡献指南](./CONTRIBUTING.zh-CN.md)
- [英文贡献指南](./CONTRIBUTING.md)
- [中文安全策略](./SECURITY.zh-CN.md)
- [英文安全策略](./SECURITY.md)

## 参与贡献

当前最适合的贡献方向包括：

- 首次上手和本地开发体验
- API 与 worker 的稳定性
- 围绕创建 -> 生成 -> 游玩的测试补充
- 减少创建和恢复流程困惑感的 UI 改进

可以直接用仓库模板发起 [Bug 报告](https://github.com/kurtxu88/parallel-worlds/issues/new?template=bug_report.yml)、[功能建议](https://github.com/kurtxu88/parallel-worlds/issues/new?template=feature_request.yml) 或 [世界展示](https://github.com/kurtxu88/parallel-worlds/issues/new?template=showcase.yml)。

如果你希望全程用中文，也可以直接使用 [中文 Bug 模板](https://github.com/kurtxu88/parallel-worlds/issues/new?template=bug_report.zh-CN.yml)、[中文功能建议模板](https://github.com/kurtxu88/parallel-worlds/issues/new?template=feature_request.zh-CN.yml) 和 [中文世界展示模板](https://github.com/kurtxu88/parallel-worlds/issues/new?template=showcase.zh-CN.yml)。
也可以直接查看 [适合新人的任务](https://github.com/kurtxu88/parallel-worlds/labels/good%20first%20issue)、[需要帮助的任务](https://github.com/kurtxu88/parallel-worlds/labels/help%20wanted) 和 [世界展示贴](https://github.com/kurtxu88/parallel-worlds/labels/showcase)。

如果你认同这个方向，给仓库点一个 star 会很有帮助，它能让更多人发现这个项目。
