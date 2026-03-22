# API

`apps/api` contains the FastAPI service for Parallel Worlds.

## Main Endpoints

- `POST /api/session/guest`
- `GET /api/stories`
- `POST /api/stories`
- `GET /api/stories/{id}`
- `POST /api/stories/{id}/retry`
- `GET /api/stories/{id}/events`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/game/interact`
- `GET /api/health`

## Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
