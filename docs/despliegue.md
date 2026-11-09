# Despliegue del dashboard y del servidor

## Arquitectura

```text
Navegador -> SvelteKit/Bun :3000 -> FastAPI :8000 -> SQLite
Clientes WireGuard -> FastAPI :8000
```

El servidor de SvelteKit guarda `API_KEY` en su entorno privado y consulta FastAPI desde el servidor.
El navegador solo habla con SvelteKit, así que no se configura CORS y la API key nunca llega al
bundle del cliente.

## Docker Compose

```bash
cp .env.example .env
# editar API_KEY en .env
docker compose up --build
```

Servicios:

| Servicio | Puerto | Función |
|---|---|---|
| `frontend` | `3000` | Dashboard SvelteKit/Bun |
| `backend` | `8000` | API FastAPI para dashboard y clientes |

El backend espera `GET /health` antes de que arranque el frontend. La base SQLite se guarda en el
volumen `overlay-db`; `docker compose down -v` borra los datos.

Los clientes se unen desde sus propias máquinas, no desde la red de Compose:

```bash
sudo python3 -m client join --server <IP-LAN-DEL-SERVIDOR>:8000 --key <API_KEY>
```

## Variables

| Variable | Servicio | Descripción |
|---|---|---|
| `API_KEY` | ambos | Bearer compartido. En el frontend solo lo usa el servidor. |
| `API_BASE_URL` | frontend | URL interna de FastAPI; en Compose es `http://backend:8000`. |
| `DATABASE_URL` | backend | En Compose es `sqlite:////data/overlay.db`. |
| `OFFLINE_AFTER_S` | backend | Segundos sin heartbeat para considerar un nodo offline. |
| `PROBE_TTL_S` | backend | Vigencia del resultado de probe. |
| `HOST` / `PORT` | frontend | Listener del servidor Bun. |

## Desarrollo local

```bash
# terminal 1
nix develop
API_KEY=devkey uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload

# terminal 2
nix develop
cd frontend
API_BASE_URL=http://127.0.0.1:8000 API_KEY=devkey bun run dev -- --host
```

El dashboard queda en `http://localhost:5173/`. El servidor de desarrollo de SvelteKit consulta
FastAPI con `API_BASE_URL`, por lo que tampoco hace falta un proxy de Vite.

## Build de producción sin Docker

```bash
cd frontend
bun install --frozen-lockfile
bun run --bun build
API_BASE_URL=http://127.0.0.1:8000 API_KEY=<API_KEY> HOST=0.0.0.0 PORT=3000 bun ./build
```

`API_KEY` es obligatoria en tiempo de ejecución (el build no la necesita). `adapter-bun` necesita
Bun 1.4.4 o superior y el build debe ejecutarse con `bun run --bun build`.

## Verificación

```bash
curl http://localhost:8000/health
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/nodes
curl http://localhost:3000/api/dashboard
```

La API key no debe aparecer en el HTML ni en los archivos de `frontend/build`:

```bash
if docker compose exec -T frontend grep -R -q "$API_KEY" /app/build; then
  echo "FUGA: la API key está en el build"
else
  echo "ok: sin API key en el build"
fi
```

## Seguridad

El dashboard no pide credenciales y muestra datos internos del overlay (IDs, IPs, claves públicas,
endpoints y estadísticas). Publícalo solo en una red de confianza o detrás de un proxy con
autenticación. El contenedor `frontend` guarda la `API_KEY` y puede escribir en FastAPI, así que
trátalo como parte del plano de control, no como un servicio público.
