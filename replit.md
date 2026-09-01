# نظام إدارة المخزن

نظام ويب داخلي عربي لإدارة مستخدمي المخزن وأدوارهم وصلاحياتهم، مع تسجيل دخول ولوحة رئيسية أولية قابلة للتوسعة.

## Run & Operate

- `uv run alembic upgrade head` — apply PostgreSQL migrations
- `uv run python -m backend.seed` — create the initial roles, permissions, and admin user
- `uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8080` — run the FastAPI server
- `pnpm --filter @workspace/warehouse-management run dev` — run the React frontend
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- Required env: `DATABASE_URL`, `SESSION_SECRET`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9, Python 3.11
- Frontend: React + Vite
- API: Python FastAPI
- DB: PostgreSQL + SQLAlchemy asyncpg
- Migrations: Alembic
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `backend/app/` — FastAPI application, session authentication, routes, models, and settings
- `backend/alembic/` — migration environment and PostgreSQL migrations
- `backend/seed.py` — initial access-control data and the first administrator
- `artifacts/warehouse-management/` — React RTL frontend
- `lib/api-spec/openapi.yaml` — source of truth for API contracts and generated client hooks
- `.env.example` — environment settings template

## Architecture decisions

- Authentication uses database-backed opaque session cookies rather than browser-stored tokens, which suits a local-network deployment.
- Role permissions are represented as a many-to-many relationship so new permissions can be added without changing user records.
- The API is mounted below `/api` and the frontend uses relative requests so the local-network proxy can route both services.

## Product

- Arabic RTL login, protected dashboard, warehouse/department/item catalogs, and Phase 3 receiving and inventory screens.
- User administration with three seeded roles: مدير النظام، أمين المخزن، موظف القسم.
- Permission checks for dashboard, catalog administration, receiving, and inventory views.

## User preferences

- Phase 3 includes receipt notes, opening-balance and receipt movements, calculated balances, serial-number uniqueness, and expiry monitoring.
- Issuing, transfers, stocktaking, and reports remain intentionally excluded.

## Gotchas

- Apply Alembic migrations before seeding or starting FastAPI.
- The seeded development administrator is `admin` / `Admin@12345`; change it after first login in a real deployment.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
