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

## Checks (run before considering any change done)

```bash
ruff format server
ruff check --fix server
ty check server
```

- `ruff`: formatter + linter, config in `pyproject.toml` (`[tool.ruff]`).
- `ty`: type checker, config in `pyproject.toml` (`[tool.ty]`).
- No comments in code unless asked; keep modules single-purpose (`config`, `schemas`, `auth`, `store/`, `routers/`).
