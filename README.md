# Parallel Worlds

Parallel Worlds is an open-source AI storytelling app built with Vue, FastAPI, Neo4j OSS, and Postgres.

The v1 open-source release focuses on a tight core loop:

- create a world seed
- generate the world asynchronously in a worker
- enter the world and play through streamed interactions
- restore prior sessions from stored event history
- save language and theme preferences for a guest identity

This repository does not include the private product history. It is a fresh public codebase with its own structure and git history.

## Stack

- `apps/web`: Vue 3 + Vite
- `apps/api`: FastAPI API and gameplay endpoint
- `workers/story-generator`: async world generation worker
- `db/postgres`: relational schema for stories, events, and settings
- `db/neo4j`: graph storage notes for generated world data
- `docker-compose.yml`: local development stack

## Quick Start

1. Copy the environment template.

```bash
cp .env.example .env
```

2. Set `OPENAI_API_KEY` in `.env`.

3. Start the local stack.

```bash
docker compose up --build
```

4. Open the app at [http://localhost:5173](http://localhost:5173).

5. Verify the API at [http://localhost:8000/api/health](http://localhost:8000/api/health).

## Guest Mode

The open-source release uses guest mode by default.

- No Supabase
- No hosted auth
- No email signup
- No invitation system

The frontend requests `POST /api/session/guest` once, stores the returned `guest_user_id` locally, and sends it back through `X-User-Id`.

## Environment Variables

Required for world generation:

- `OPENAI_API_KEY`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`

Required for story/event/settings storage:

- `DATABASE_URL`

Frontend:

- `VITE_API_BASE_URL`

See `.env.example` for local defaults.

## Repo Layout

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

## Current Scope

Included in v1:

- guest session creation
- personal world list
- async generation worker
- streamed play sessions
- history restore
- language/theme settings

Not included in v1:

- public world marketplace
- invitations
- email/password auth
- hosted deployment defaults

## Local Development

Frontend only:

```bash
cd apps/web
npm install
npm run dev
```

API only:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Worker only:

```bash
cd workers/story-generator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python worker.py
```

## Docs

- [Architecture](./docs/architecture.md)
- [Chinese README](./README.zh-CN.md)
- [Contributing](./CONTRIBUTING.md)
- [Security](./SECURITY.md)
