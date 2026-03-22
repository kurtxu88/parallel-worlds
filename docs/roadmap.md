# Roadmap

Parallel Worlds is being built in public as a compact open-source AI storytelling stack.

The goal is not to grow into a giant framework overnight. The goal is to keep shipping a playable, hackable system that gets easier to run, easier to extend, and more interesting to share with each release.

## Product Direction

We are focusing on four qualities:

- strong first-run experience
- playable worlds rather than static text demos
- clean boundaries between web, API, worker, and storage
- contributor-friendly scope that stays understandable

## Now

These are the highest-priority improvements for the next public releases:

- make first-run onboarding smoother with starter seeds, clearer docs, and faster local setup
- improve observability around generation failures and retry flows
- add more test coverage for the API and worker core loop
- publish better demo assets so the project is easier to understand at a glance

## Next

Once the core loop feels solid, the next milestone is shareability:

- public browsing and discovery on top of share pages
- export and import for generated worlds
- richer example seeds and canonical demo scenarios
- better world metadata, titles, and summaries for browsing

## Later

Longer-term work should expand the project without making the open-source surface area confusing:

- extension points for custom generators or prompt packs
- story/world templates for different genres
- deployment guides for self-hosted and small-team setups
- deeper monitoring and operational tooling for worker jobs

## Not In Immediate Scope

The public v1 intentionally does not prioritize:

- hosted auth defaults
- invitation systems
- private SaaS-only workflows

If a proposal depends on those, open an issue first so we can align on the tradeoffs before implementation.

## Good Contributions Right Now

The most helpful contributions in the current phase are:

- fixes that make the first local run more reliable
- tests around story generation state transitions
- UI improvements that reduce confusion during create, wait, and play flows
- docs improvements with concrete examples and troubleshooting notes

## How We Decide What Ships

We will generally favor changes that improve one or more of these:

- demoability: can someone understand the project quickly and show it to someone else?
- repeatability: can contributors run and verify the same workflow locally?
- extensibility: does the change make it easier to build on top of the core loop?
- clarity: does it keep the public codebase easier to learn rather than harder?
