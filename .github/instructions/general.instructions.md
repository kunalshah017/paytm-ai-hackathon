---
description: General project structure, conventions, and guidelines for the Paytm AI Hackathon monorepo
applyTo: "**"
---

# Paytm AI Hackathon — Project Instructions

## Project Overview

This is a monorepo for a hackathon project with two main parts:

- **`server/`** — Python FastAPI backend
- **`client/`** — Vite + React frontend

## Tech Stack

| Layer    | Technology                               |
| -------- | ---------------------------------------- |
| Backend  | Python 3.11+, FastAPI, Uvicorn, uv       |
| Frontend | React 18, TypeScript, Vite, React Router |
| Database | PostgreSQL (Supabase), SQLAlchemy async  |
| API Comm | Axios (client) ↔ REST (server)           |

## Server (`server/`)

### Structure

```
server/
├── app/
│   ├── api/          # Route handlers & dependencies
│   │   ├── routes.py
│   │   └── deps.py
│   ├── models/       # Data / DB models
│   ├── schemas/      # Pydantic request/response schemas
│   ├── services/     # Business logic layer
│   ├── utils/        # Shared helpers
│   ├── config.py     # Settings via pydantic-settings
│   └── main.py       # FastAPI app entry point
├── run.py            # Dev runner (uvicorn with reload)
├── pyproject.toml    # Project config & dependencies (managed by uv)
└── .env.example
```

### Conventions

- Add new route groups as separate files under `app/api/` and register them in `routes.py`.
- Keep business logic in `app/services/`, not in route handlers.
- Define request/response models in `app/schemas/`.
- Use dependency injection via `app/api/deps.py` for shared resources (DB, auth, etc.).
- Environment variables are managed through `.env` (copy `.env.example`).
- Database models live in `app/models/` and use SQLAlchemy async with `asyncpg`.
- Tables are auto-created on startup via `init_db()` in `app/database/database.py`.

### API Routing

- All API routes are prefixed with `/api` (set in `main.py` via `app.include_router(router, prefix="/api")`).
- Route groups use their own `APIRouter` with a sub-prefix (e.g., `APIRouter(prefix="/inventory")`).
- FastAPI auto-generates a trailing-slash redirect (307) for routes defined with `/`. **Always use trailing slashes in client API calls** (e.g., `/api/inventory/`, not `/api/inventory`) to avoid unnecessary redirects.

### SPA Serving (Production)

- In production, the server serves the built React client from `client/dist/`.
- Static assets are mounted at `/assets`.
- A custom 404 exception handler serves `index.html` for non-API routes (SPA fallback).
- API 404s return JSON `{"detail": "Not found"}` — the handler explicitly checks `request.url.path.startswith("/api")`.
- **Never** use a catch-all `/{path:path}` route — it conflicts with the API router.

### Running

```bash
cd server
uv sync
cp .env.example .env
uv run python run.py
```

Server runs at `http://localhost:8000`. Health check: `GET /health`.

### Testing

Run server tests with `uv run pytest`. Place test files in `server/tests/` mirroring the `app/` structure.

### Adding Dependencies

```bash
uv add <package-name>
uv add --dev <package-name>  # for dev-only deps
```

## Client (`client/`)

### Structure

```
client/
├── public/
├── src/
│   ├── assets/       # Static assets (images, icons, fonts)
│   ├── components/   # Reusable UI components
│   ├── hooks/        # Custom React hooks
│   ├── pages/        # Route-level page components
│   ├── services/     # API service layer (axios instances)
│   ├── utils/        # Helper functions
│   ├── App.tsx       # Root component with routing
│   ├── main.tsx      # Entry point
│   └── index.css     # Global styles
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── .env.example
```

### Conventions

- One page component per route in `src/pages/`.
- Reusable UI goes in `src/components/`.
- All API calls go through the axios instance in `src/services/api.ts`.
- **Always use trailing slashes** in API paths (e.g., `api.get("/api/inventory/")`) to avoid 307 redirects.
- Always provide fallback defaults when reading API responses (e.g., `res.data || []`) to handle null/undefined safely.
- Use `@/` alias for imports from `src/`.
- Use TypeScript for all source files (`.tsx` for components, `.ts` for logic).
- The Vite proxy is configured in `vite.config.ts` to forward all `/api/*` requests to `http://localhost:8000`. Server routes should be prefixed with `/api`. No additional CORS configuration is needed in development due to the proxy.

### Running

```bash
cd client
npm install
cp .env.example .env
npm run dev
```

Client runs at `http://localhost:5173`.

### Testing

Run client tests with `npm run test`. Place test files adjacent to source files with `.test.ts` or `.test.tsx` suffix.

## Git & Commit History Guidelines

**Maintain a clean, meaningful commit history.** This is critical for hackathon judging and collaboration.

### Commit Message Format

```
<type>: <short summary>

[optional body with more context]
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `style`, `chore`, `test`

### Rules

1. **Atomic commits** — Each commit should represent one complete, self-contained logical change (e.g., a full feature, a single bug fix, or one refactoring step). Break large features into smaller logical units, each of which leaves the codebase in a working state.
2. **No WIP commits on main** — Use branches for work-in-progress.
3. **Never force-push to `main`** without team agreement.
4. **Write meaningful messages** — Future reviewers (and judges) will read them.

### Examples

```
feat: add user authentication endpoint
fix: resolve CORS issue with preflight requests
chore: add axios dependency to client
docs: update README with setup instructions
```

## General Coding Guidelines

- Do not leave dead code or commented-out blocks.
- Handle errors at API boundaries; return proper HTTP status codes from the server.
- Keep secrets out of code — use `.env` files (never commit them).
- When adding a new feature that involves API communication, ensure corresponding changes are made in both `server/` and `client/`. Pure backend logic or pure UI changes that don't cross the API boundary may be committed independently.
- Prefer simple, readable code over clever abstractions — this is a hackathon.
