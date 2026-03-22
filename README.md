# Parallel Worlds

[![CI](https://github.com/kurtxu88/parallel-worlds/actions/workflows/ci.yml/badge.svg)](https://github.com/kurtxu88/parallel-worlds/actions/workflows/ci.yml)
[![Release Drafter](https://github.com/kurtxu88/parallel-worlds/actions/workflows/release-drafter.yml/badge.svg)](https://github.com/kurtxu88/parallel-worlds/actions/workflows/release-drafter.yml)
[![Release](https://github.com/kurtxu88/parallel-worlds/actions/workflows/release.yml/badge.svg)](https://github.com/kurtxu88/parallel-worlds/actions/workflows/release.yml)
[![GitHub stars](https://img.shields.io/github/stars/kurtxu88/parallel-worlds?style=social)](https://github.com/kurtxu88/parallel-worlds/stargazers)

![Parallel Worlds social card](./apps/web/public/social-card.svg)

Parallel Worlds is an open-source AI storytelling app for building playable worlds from short narrative seeds.

Current release line: `v0.1.0`

It uses Vue, FastAPI, Neo4j OSS, and Postgres to support a tight loop:

- create a world seed
- generate the world asynchronously in a worker
- enter the world and play through streamed interactions
- restore prior sessions from stored event history
- save language and theme preferences for a guest identity

This repository does not include the private product history. It is a fresh public codebase with its own structure and git history, designed to keep shipping in public.

## Why This Project Exists

Most AI story demos stop at one-shot generation. Parallel Worlds is trying to keep the world itself alive:

- Postgres stores users, stories, settings, and event history
- Neo4j stores the world graph used during play
- the API and worker stay separate so generation and play can evolve independently
- guest mode keeps the open-source version easy to run locally

If you care about open-source story engines, graph-backed narrative systems, or small full-stack AI products that are actually hackable, this project is for you.

## Project Status

Parallel Worlds is in an active early public phase.

- The current release is a focused v1
- The roadmap is intentionally small and shippable
- New improvements should make the project easier to run, easier to demo, and easier to extend

See [Roadmap](./docs/roadmap.md) for the current direction.

## Stack

- `apps/web`: Vue 3 + Vite
- `apps/api`: FastAPI API and gameplay endpoint
- `workers/story-generator`: async world generation worker
- `db/postgres`: relational schema for stories, events, and settings
- `db/neo4j`: graph storage notes for generated world data
- `docker-compose.yml`: local development stack

## Current Scope

Included in v1:

- guest session creation
- personal world list
- async generation worker
- streamed play sessions
- history restore
- language/theme settings
- opt-in public share pages for individual worlds

Not included in v1:

- public world marketplace
- invitations
- email/password auth
- hosted deployment defaults

## Quick Start

Requirements:

- Docker
- an `OPENAI_API_KEY`

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

The `.env.example` values are Docker Compose friendly by default.

## Try This Seed

Use this example to get a fast first run:

```json
{
  "user_input": "An archivist on a drowned moon keeps discovering records of wars that have not happened yet.",
  "gender_preference": "female",
  "culture_language": "en-US"
}
```

You can also deep-link directly into a starter seed page such as `/create?seed=drowned-moon`.
If you enable sharing while creating a world, you can also publish it at `/share/<story-id>`.
Published worlds can also be browsed from the public discovery feed at `/discover`.

## Guest Mode

The open-source release uses guest mode by default.

- No Supabase
- No hosted auth
- No email signup
- No invitation system

The frontend requests `POST /api/session/guest` once, stores the returned `guest_user_id` locally, and sends it back through `X-User-Id`.
Public world pages are optional and opt-in per story, and shared worlds can be browsed through `/discover`.

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
- `VITE_PUBLIC_SITE_URL` for canonical and social preview URLs in production

See `.env.example` for local defaults.

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
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://parallel_worlds:parallel_worlds@localhost:5432/parallel_worlds
export NEO4J_URI=bolt://localhost:7687
uvicorn main:app --reload
```

Worker only:

```bash
cd workers/story-generator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://parallel_worlds:parallel_worlds@localhost:5432/parallel_worlds
export NEO4J_URI=bolt://localhost:7687
python3 worker.py
```

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

## Docs

- [Architecture](./docs/architecture.md)
- [Roadmap](./docs/roadmap.md)
- [Growth Playbook](./docs/growth-playbook.md)
- [Demo Script](./docs/demo-script.md)
- [Launch Checklist](./docs/launch-checklist.md)
- [Release Process](./docs/release-process.md)
- [Chinese README](./README.zh-CN.md)
- [Contributing](./CONTRIBUTING.md)
- [Chinese Contributing Guide](./CONTRIBUTING.zh-CN.md)
- [Security](./SECURITY.md)
- [Chinese Security Policy](./SECURITY.zh-CN.md)

## Contributing

Small, focused improvements are the best fit right now.

- onboarding and developer experience
- API and worker reliability
- tests around the create -> generate -> play loop
- UI clarity during story creation and recovery

Use the repo templates to open a [bug report](https://github.com/kurtxu88/parallel-worlds/issues/new?template=bug_report.yml), [feature request](https://github.com/kurtxu88/parallel-worlds/issues/new?template=feature_request.yml), or [world showcase](https://github.com/kurtxu88/parallel-worlds/issues/new?template=showcase.yml).
You can also browse [good first issues](https://github.com/kurtxu88/parallel-worlds/labels/good%20first%20issue), [help wanted tasks](https://github.com/kurtxu88/parallel-worlds/labels/help%20wanted), and [showcase posts](https://github.com/kurtxu88/parallel-worlds/labels/showcase).

If this direction is useful to you, starring the repo helps more people discover it.
