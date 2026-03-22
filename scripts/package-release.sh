#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-$(cat "$ROOT_DIR/VERSION")}"
RELEASE_DIR="$ROOT_DIR/out/release/$VERSION"
NPM_CACHE_DIR="$ROOT_DIR/.npm-cache"

mkdir -p "$RELEASE_DIR"
mkdir -p "$NPM_CACHE_DIR"
rm -f "$RELEASE_DIR"/*

(
  cd "$ROOT_DIR/apps/web"
  export NPM_CONFIG_CACHE="$NPM_CACHE_DIR"
  npm ci
  npm run build
)

tar -czf "$RELEASE_DIR/parallel-worlds-src-v$VERSION.tar.gz" \
  --exclude=".git" \
  --exclude=".npm-cache" \
  --exclude="out" \
  --exclude="apps/web/node_modules" \
  --exclude="apps/web/dist" \
  --exclude="apps/api/__pycache__" \
  --exclude="workers/story-generator/__pycache__" \
  -C "$ROOT_DIR" \
  .

(
  cd "$ROOT_DIR/apps/web/dist"
  zip -qr "$RELEASE_DIR/parallel-worlds-web-dist-v$VERSION.zip" .
)

(
  cd "$RELEASE_DIR"
  shasum -a 256 \
    "parallel-worlds-src-v$VERSION.tar.gz" \
    "parallel-worlds-web-dist-v$VERSION.zip" \
    > "checksums.txt"
)

echo "Release assets created in $RELEASE_DIR"
