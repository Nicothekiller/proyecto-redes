# Dashboard (SvelteKit + Bun)

Server-rendered dashboard for the WireGuard coordination server. The SvelteKit server queries
FastAPI with the key entered at `/login`: `DASHBOARD_API_KEY` for read-only access, or `API_KEY`
for admin access. The browser never talks to FastAPI directly and no CORS is needed.

## Development

```bash
bun install --frozen-lockfile
API_BASE_URL=http://127.0.0.1:8000 bun run dev -- --host
```

Open `http://localhost:5173/`.

## Production

```bash
bun install --frozen-lockfile
bun run --bun build
API_BASE_URL=http://127.0.0.1:8000 HOST=0.0.0.0 PORT=3000 bun ./build
```

No key is required in the frontend environment. Login requires JavaScript.
`adapter-bun` requires Bun 1.4.4+
and the build must run with `bun run --bun build`.

## Checks

```bash
bun run check
bun run lint
bun run --bun build
```

See `../docs/despliegue.md` for Docker Compose.
