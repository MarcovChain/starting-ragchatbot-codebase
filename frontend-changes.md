# Frontend Changes

## Code Quality Tooling

### Tools Added

| Tool | Purpose | Config file |
|---|---|---|
| **Prettier** | Automatic code formatting (JS, CSS, HTML) | `frontend/.prettierrc` |
| **ESLint** | JavaScript static analysis | `frontend/eslint.config.js` |

### New Files

- `frontend/package.json` — npm project with dev dependencies and quality scripts
- `frontend/.prettierrc` — Prettier config (100-char width, 2-space indent, single quotes, trailing commas)
- `frontend/eslint.config.js` — ESLint flat config for browser globals, `no-unused-vars`, `eqeqeq`, `prefer-const`
- `scripts/check-frontend.sh` — shell script that runs Prettier check + ESLint in one command

### npm Scripts (run from `frontend/`)

```bash
npm run format        # format all files in-place
npm run format:check  # check formatting without writing (CI-safe)
npm run lint          # lint script.js
npm run lint:fix      # auto-fix lint issues
npm run quality       # format:check + lint (full gate)
```

### Quality Check Script (run from repo root)

```bash
./scripts/check-frontend.sh
```

Installs dependencies automatically if `node_modules` is missing, then runs Prettier check and ESLint.

### Formatting Applied

All three frontend files were reformatted to match Prettier's output:

- **`script.js`** — 4-space → 2-space indent; collapsed redundant blank lines; trailing commas on multi-line object/array literals; consistent single quotes; arrow function params always parenthesised
- **`style.css`** — 4-space → 2-space indent; `*::before, *::after` selector expanded to one-per-line; single-property heading rules expanded; `@keyframes` selector groups expanded
- **`index.html`** — 4-space → 2-space indent; long `<button>` and `<svg>` attribute lists wrapped one-per-line; `<!DOCTYPE html>` lowercased to `<!doctype html>`; void elements self-closed (`<meta … />`, `<input … />`)

### Prerequisites

Node.js and npm must be installed to use the tooling. Install dependencies once:

```bash
cd frontend && npm install
```
