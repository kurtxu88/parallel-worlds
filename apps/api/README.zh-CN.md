# API

`apps/api` 是 Parallel Worlds 的 FastAPI 服务。

## 主要接口

- `POST /api/session/guest`
- `GET /api/stories`
- `POST /api/stories`
- `GET /api/stories/{id}`
- `POST /api/stories/{id}/retry`
- `PATCH /api/stories/{id}/visibility`
- `GET /api/public/stories`
- `GET /api/stories/{id}/events`
- `GET /api/public/stories/{id}`
- `GET /api/public/stories/{id}/events`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/game/interact`
- `GET /api/health`

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://parallel_worlds:parallel_worlds@localhost:5432/parallel_worlds
export NEO4J_URI=bolt://localhost:7687
uvicorn main:app --reload
```
