# Release Process

This repository now has a real version and release flow.

## Current Version

The canonical project version lives in:

- `VERSION`
- `apps/web/package.json`

These must stay in sync. Use:

```bash
python3 scripts/verify-version.py
```

## Release Assets

Each release should publish:

- `parallel-worlds-src-vX.Y.Z.tar.gz`
- `parallel-worlds-web-dist-vX.Y.Z.zip`
- `checksums.txt`

To build them locally:

```bash
bash scripts/package-release.sh
```

Or for a specific version:

```bash
bash scripts/package-release.sh 0.1.0
```

## GitHub Release Flow

The release workflow lives at:

- `.github/workflows/release.yml`

It runs on:

- tag pushes matching `v*`
- manual `workflow_dispatch`

The workflow will:

1. verify the version files
2. run the web build and tests
3. compile-check the Python code
4. build release archives
5. upload artifacts
6. publish a GitHub Release

## Recommended Release Steps

1. Update `CHANGELOG.md`
2. Update `VERSION`
3. Update `apps/web/package.json`
4. Run:

```bash
python3 scripts/verify-version.py
cd apps/web && npm run build && npm run test
python3 -m compileall apps/api workers/story-generator
bash scripts/package-release.sh
```

5. Commit the release changes
6. Push the commit
7. Push tag `vX.Y.Z`

## Why This Matters

Releases make the project easier to trust, easier to reference, and easier to share.

For open-source growth, a repo that ships visible versions feels alive in a way that a repo with only commits does not.
