#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/release"
PKG_NAME="bilibili-comment-platform-2026-06-06"
STAGE_DIR="$OUT_DIR/$PKG_NAME"
ARCHIVE_PATH="$OUT_DIR/${PKG_NAME}.tar.gz"

rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"
mkdir -p "$OUT_DIR"

copy_path() {
  local src="$1"
  local dst="$STAGE_DIR/$1"
  mkdir -p "$(dirname "$dst")"
  cp -R "$ROOT_DIR/$src" "$dst"
}

copy_path "README.md"
copy_path ".env.example"
copy_path ".dockerignore"
copy_path ".gitignore"
copy_path "Makefile"
copy_path "docker-compose.yml"
copy_path "backend"
copy_path "frontend"
copy_path "deploy"
copy_path "vendor"
copy_path "docs"

rm -rf "$STAGE_DIR/backend/.pytest_cache"
rm -rf "$STAGE_DIR/backend/bilibili_comment_platform.egg-info"
rm -rf "$STAGE_DIR/frontend/node_modules"
rm -rf "$STAGE_DIR/frontend/dist"
rm -f "$STAGE_DIR/frontend/tsconfig.app.tsbuildinfo"
rm -rf "$STAGE_DIR/vendor/bilibili-api/.git"
rm -rf "$STAGE_DIR/vendor/bilibili-api/.github"
rm -rf "$STAGE_DIR/vendor/bilibili-api/.githooks"
rm -rf "$STAGE_DIR/vendor/bilibili-api/bilibili_api_python.egg-info"
find "$STAGE_DIR/backend" -maxdepth 1 -name '*.db' -delete

tar -C "$OUT_DIR" -czf "$ARCHIVE_PATH" "$PKG_NAME"
echo "$ARCHIVE_PATH"
