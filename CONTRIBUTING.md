# Contributing

Thanks for helping build Parallel Worlds.

## Before You Start

- Read [README.md](./README.md)
- Read [docs/roadmap.md](./docs/roadmap.md)
- Read [docs/growth-playbook.md](./docs/growth-playbook.md) if your change is aimed at adoption, demoability, or community growth
- Use the open-source stack in this repo only
- Do not reintroduce hosted auth or Supabase defaults into v1

## Setup

1. Copy `.env.example` to `.env`
2. Set `OPENAI_API_KEY`
3. Start services with `docker compose up --build`
4. For frontend-only work, use `cd apps/web && npm install && npm run dev`

## Development Expectations

- Keep changes scoped and easy to review
- Prefer clear APIs over hidden defaults
- Avoid committing secrets, production URLs, or real credentials
- Preserve guest-mode behavior unless the change explicitly expands auth

## Pull Requests

- Explain the problem and the user-facing change
- Mention any schema or environment changes
- Include test coverage when practical
- Keep documentation in sync with behavior
- Keep PRs focused enough to review in one sitting

## Checks

Before opening a PR, run:

```bash
cd apps/web && npm install && npm run build && npm run test
python3 -m compileall apps/api workers/story-generator
```

## Scope Notes

The first public release intentionally excludes:

- invitations
- public world marketplace
- hosted auth flows

If you want to propose one of those, open an issue first so we can align on the design.
