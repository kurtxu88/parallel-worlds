# 排障指南

这份文档整理的是 Parallel Worlds 当前最常见的本地运行和贡献者问题。

## Docker 栈启动不起来

常见现象：

- `docker compose up --build` 很快退出
- 某个服务反复重启
- `5173`、`8000`、`5432`、`7474`、`7687` 这些端口已经被占用

优先检查：

- 确认 Docker Desktop 已经启动
- 确认 `.env` 存在，并且已经填写 `OPENAI_API_KEY`
- 如果你是从 `.env.example` 复制出来的，Docker Compose 场景下不要把容器主机名改回 `localhost`
- 检查本机是不是已经有别的 Postgres、Neo4j 或 Vite 进程占用了同样端口

常用命令：

```bash
docker compose ps
docker compose logs -f api worker web
```

## 前端连不上 API

常见现象：

- 页面能打开，但访客会话创建失败
- 世界列表或设置加载失败
- 浏览器控制台里出现指向 `localhost:8000` 的网络错误

优先检查：

- 如果你跑的是整套 Docker 栈，请优先使用 `.env.example` 的默认值
- 如果你是在 Docker 外单独运行 `apps/web`，请设置 `VITE_API_BASE_URL=http://localhost:8000`
- 直接访问 `http://localhost:8000/api/health`，确认 API 是否真的活着

## 故事一直卡在 `pending`

常见现象：

- 世界已经创建，但一直不完成生成
- 状态停留在 `pending`，或者点 retry 后还是反复失败

优先检查：

- 确认 `worker` 服务正在运行
- 确认 `.env` 里的 `OPENAI_API_KEY` 已正确填写
- 同时看 `worker` 和 `api` 日志，因为任务领取和失败信息可能出现在任意一边

常用命令：

```bash
docker compose logs -f worker api
```

## 公开分享页或发现页返回 `404`

常见现象：

- `/share/<story-id>` 打开后提示找不到
- `/discover` 里没有看到你以为已经公开的世界

优先检查：

- 先确认这个世界已经在 `My Worlds` 里被切到公开状态
- 确认你复制的分享链接里 `story-id` 没有错
- 私有世界本来就不会暴露给公开接口，这是刻意的保护行为
- 如果是刚刚切成公开，等可见性更新完成后再刷新一次页面

## 本地做 API 开发时 Python 导入失败

常见现象：

- 在 `apps/api` 里工作时遇到 `ModuleNotFoundError`
- 测试命令还没开始跑就先报缺模块

优先检查：

- 在 `apps/api` 内创建并激活虚拟环境
- 安装 `requirements.txt` 里的依赖

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m unittest discover tests
```

## 常看的日志位置

- `docker compose logs -f api`
- `docker compose logs -f worker`
- `docker compose logs -f web`
- 前端请求失败时，也要看浏览器 devtools 的 network 面板

如果你遇到的问题不在上面这些情况里，最有帮助的反馈方式是：把运行命令、报错日志、你的运行模式一起贴到 issue 里。
