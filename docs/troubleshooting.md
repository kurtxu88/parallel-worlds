# Troubleshooting

This guide is for the most common local-run and contributor issues in Parallel Worlds.

## Docker Stack Will Not Start

Symptoms:

- `docker compose up --build` exits quickly
- one or more services restart in a loop
- ports such as `5173`, `8000`, `5432`, `7474`, or `7687` are already in use

What to check:

- make sure Docker Desktop is running
- make sure `.env` exists and includes `OPENAI_API_KEY`
- if you copied `.env.example`, keep the default container hostnames for Docker Compose
- check whether another local Postgres, Neo4j, or Vite process is already using the same ports

Useful commands:

```bash
docker compose ps
docker compose logs -f api worker web
```

## Frontend Cannot Reach the API

Symptoms:

- the app loads but guest session creation fails
- story lists or settings fail to load
- browser console shows network errors for `localhost:8000`

What to check:

- if you are running the full Docker stack, use the defaults from `.env.example`
- if you are running `apps/web` outside Docker, set `VITE_API_BASE_URL=http://localhost:8000`
- verify the API directly at `http://localhost:8000/api/health`

## Stories Stay in `pending`

Symptoms:

- a world is created but never finishes generation
- the story remains in `pending` or keeps failing after retry

What to check:

- confirm the `worker` service is running
- confirm `OPENAI_API_KEY` is set correctly in `.env`
- inspect worker and API logs together, because claim/failure details may appear in either service

Useful commands:

```bash
docker compose logs -f worker api
```

## Public Share or Discovery Pages Return `404`

Symptoms:

- `/share/<story-id>` returns not found
- `/discover` does not show a world you expected to be public

What to check:

- make sure the story has been marked public from `My Worlds`
- verify you copied the correct story ID in the share URL
- note that private stories are intentionally hidden from public endpoints
- if a world was just published, refresh the page after the visibility update finishes

## Python API Imports Fail During Local Work

Symptoms:

- `ModuleNotFoundError` while working inside `apps/api`
- test commands fail before they even start

What to check:

- create and activate a virtual environment inside `apps/api`
- install dependencies from `requirements.txt`

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m unittest discover tests
```

## Good Log Locations

- `docker compose logs -f api`
- `docker compose logs -f worker`
- `docker compose logs -f web`
- browser devtools network tab for frontend request failures

If you hit something outside these cases, opening an issue with exact commands, logs, and your run mode helps a lot.
