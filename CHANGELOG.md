# Changelog

All notable public-facing changes to Parallel Worlds should be summarized here.

The goal is not exhaustive internal detail. The goal is to help contributors and new visitors understand how the project is moving.

## Unreleased

### Added

- public discovery feed on `/discover` for browsing shared worlds
- public API listing endpoint at `GET /api/public/stories`
- maintainer continuity docs, repo CODEOWNERS, and Dependabot config
- English and Chinese troubleshooting guides for contributors
- API regression tests for public visibility and public endpoints

## v0.1.0 - 2026-03-22

### Added

- stronger public README positioning in English and Chinese
- roadmap, growth playbook, and demo script docs
- issue templates for bugs, features, and showcases
- release drafter workflow and config
- starter seed gallery on the create page
- shareable seed deep links on `/create`
- opt-in public share pages on `/share/:id`
- social preview asset and page SEO helpers

### Changed

- Docker Compose defaults in `.env.example` now match the container network
- story detail copy no longer references private-product premium flows
