# Web App

Web 应用是 Parallel Worlds 的 Vue 3 + Vite 前端。

## 常用命令

```bash
npm install
npm run dev
npm run build
npm run test
```

## 运行时约定

前端需要以下环境变量：

- `VITE_API_BASE_URL`
- `VITE_PUBLIC_SITE_URL`，用于生产环境的 canonical 和社交预览链接

开源版前端不会直接连接 Supabase、Postgres 或 Neo4j。

## 主要路由

- `/create`
- `/worlds`
- `/world/:id`
- `/share/:id`
