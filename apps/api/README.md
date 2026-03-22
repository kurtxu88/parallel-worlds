# API

`apps/api` contains the FastAPI service for Parallel Worlds.

## Main Endpoints

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

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://parallel_worlds:parallel_worlds@localhost:5432/parallel_worlds
export NEO4J_URI=bolt://localhost:7687
uvicorn main:app --reload
```

## Tests

```bash
python3 -m unittest discover tests
```
