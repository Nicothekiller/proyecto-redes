# AGENTS.md

## Environment

All work happens inside the nix devshell (Ubuntu + NixOS behave the same):

```bash
nix develop
```

Never `pip install` or hand-roll `nix-shell -p`. Add dependencies to `flake.nix` instead.

## Run

```bash
nix develop
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

`API_KEY` comes from the environment or a `.env` file at the repo root (env var wins).

Client (Linux, root for WireGuard):

```bash
nix develop
sudo python3 -m client join --server <IP> --key <API_KEY>
```

State lives in `/var/lib/overlay-client` (`OVERLAY_STATE_DIR` or `--state-dir` to change it).

## Dashboard

The SvelteKit dashboard is a server-rendered Bun app. Login accepts `DASHBOARD_API_KEY` (read-only)
or `API_KEY` (admin), stores it in an HttpOnly cookie and proxies requests to FastAPI
(`API_BASE_URL=http://127.0.0.1:8000` by default). The browser never talks to FastAPI directly.

```bash
# terminal 1
API_KEY=devkey DASHBOARD_API_KEY=dashboard-devkey uvicorn server.main:app --host 127.0.0.1 --port 8000

# terminal 2
cd frontend
API_BASE_URL=http://127.0.0.1:8000 bun run dev -- --host
```

Production:

```bash
cd frontend
bun install --frozen-lockfile
bun run --bun build
API_BASE_URL=http://127.0.0.1:8000 HOST=0.0.0.0 PORT=3000 bun ./build
```

## Docker Compose

```bash
cp .env.example .env
# Set API_KEY and optionally DASHBOARD_API_KEY in .env
docker compose up --build
```

- Dashboard: `http://<host>:3000/`
- API for clients: `http://<host>:8000/`
- Clients join with `sudo python3 -m client join --server <host>:8000 --key <API_KEY>`
- SQLite data lives in the `overlay-db` volume; `docker compose down -v` resets it.
- See `docs/despliegue.md`.

## Checks (run before considering any change done)

```bash
ruff format server client tests
ruff check --fix server client tests
ty check server client tests
pytest

cd frontend
bun run check
bun run lint
bun run --bun build
```

- `ruff`: formatter + linter, config in `pyproject.toml` (`[tool.ruff]`).
- `ty`: type checker, config in `pyproject.toml` (`[tool.ty]`).
- No comments in code unless asked; keep modules single-purpose (`config`, `schemas`, `auth`, `store/`, `routers/`; client: `state`, `wg`, `api`, `netinfo`, `render`, `loop`, `stats`, `probe`, `cli`).
