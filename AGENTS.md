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

## Checks (run before considering any change done)

```bash
ruff format server client tests
ruff check --fix server client tests
ty check server client tests
pytest
```

- `ruff`: formatter + linter, config in `pyproject.toml` (`[tool.ruff]`).
- `ty`: type checker, config in `pyproject.toml` (`[tool.ty]`).
- No comments in code unless asked; keep modules single-purpose (`config`, `schemas`, `auth`, `store/`, `routers/`; client: `state`, `wg`, `api`, `netinfo`, `render`, `loop`, `stats`, `probe`, `cli`).
