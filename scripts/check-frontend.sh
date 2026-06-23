#!/usr/bin/env bash
# Run all frontend code quality checks.
# Requires Node.js and npm. Run `npm install` in frontend/ first.

set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"

echo "==> Frontend quality checks"

cd "$FRONTEND_DIR"

if [ ! -d node_modules ]; then
  echo "Installing dependencies..."
  npm install
fi

echo ""
echo "--- Prettier (format check) ---"
npm run format:check

echo ""
echo "--- ESLint (lint) ---"
npm run lint

echo ""
echo "All checks passed."
