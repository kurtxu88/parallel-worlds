# Architecture

## High-Level Flow

1. The web app creates or restores a guest identity.
2. The user submits a world seed to `POST /api/stories`.
3. Postgres stores the story as `pending`.
4. The story worker claims the pending job and generates the world graph.
5. The worker imports graph data into Neo4j and marks the story `completed`.
6. The user opens the world and interacts through `POST /api/game/interact`.
7. The API stores interaction events in Postgres for history restore.

## Storage Split

### Postgres

- guest identities
- story records and generation state
- story event history
- user settings

### Neo4j

- world graph generated for each story
- scenes, links, transitions, and narrative structure used during play

## API Surface

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

## Frontend Model

The web app does not talk to Postgres or Neo4j directly.

- All reads and writes go through FastAPI
- The guest user id is stored in `localStorage`
- Story generation progress uses polling rather than realtime subscriptions

## Open-Source v1 Boundaries

Included:

- guest mode
- single-user local operation
- local Docker-based development

Deferred:

- public world sharing
- invitations
- hosted auth providers
