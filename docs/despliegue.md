# Despliegue del dashboard y del servidor

## Arquitectura

```text
Navegador -> SvelteKit/Bun :3000 -> FastAPI :8000 -> SQLite
Clientes WireGuard -> FastAPI :8000
```

El navegador solo habla con SvelteKit. En `/login` se introduce `DASHBOARD_API_KEY` para una sesión
de lectura o `API_KEY` para una sesión de administrador. La clave se guarda en una cookie HttpOnly
y SvelteKit la utiliza para consultar FastAPI; no se incluye en el bundle del cliente.

## Docker Compose

```bash
cp .env.example .env
# configurar API_KEY y, si se desea acceso de lectura, DASHBOARD_API_KEY en .env
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
| `API_KEY` | backend | Clave de los clientes; permite lectura y escritura. |
| `DASHBOARD_API_KEY` | backend | Clave distinta, para iniciar sesión de lectura y leer `/nodes` y `/status`. |
| `API_BASE_URL` | frontend | URL interna de FastAPI; en Compose es `http://backend:8000`. |
| `DATABASE_URL` | backend | En Compose es `sqlite:////data/overlay.db`. |
| `OFFLINE_AFTER_S` | backend | Segundos sin heartbeat para considerar un nodo offline. |
| `PROBE_TTL_S` | backend | Vigencia del resultado de probe. |
| `HOST` / `PORT` | frontend | Listener del servidor Bun. |

## Desarrollo local

```bash
# terminal 1
nix develop
API_KEY=devkey DASHBOARD_API_KEY=dashboard-devkey uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload

# terminal 2
nix develop
cd frontend
API_BASE_URL=http://127.0.0.1:8000 bun run dev -- --host
```

El dashboard queda en `http://localhost:5173/`. El servidor de desarrollo de SvelteKit consulta
FastAPI con `API_BASE_URL`, por lo que tampoco hace falta un proxy de Vite.

## Build de producción sin Docker

```bash
cd frontend
bun install --frozen-lockfile
bun run --bun build
API_BASE_URL=http://127.0.0.1:8000 HOST=0.0.0.0 PORT=3000 bun ./build
```

El frontend no necesita claves en su entorno. El login requiere JavaScript. `adapter-bun` necesita
Bun 1.4.4 o superior y el build debe ejecutarse con `bun run --bun build`.

## Verificación

```bash
curl http://localhost:8000/health
curl -H "Authorization: Bearer $DASHBOARD_API_KEY" http://localhost:8000/nodes
curl -i http://localhost:3000/api/dashboard # 401 sin sesión
```

## Seguridad

El dashboard muestra datos internos del overlay. La cookie HttpOnly caduca en el navegador después
de 12 horas; cambiar la clave invalida la sesión. HTTP no cifra la clave ni la cookie: usa una red de
confianza o HTTPS. La clave del dashboard no permite registrar, modificar ni eliminar nodos. Los
administradores pueden eliminar desde la interfaz nodos sin heartbeat reciente; primero se debe
apagar WireGuard en el nodo. El backend puede arrancar sin `DASHBOARD_API_KEY` cuando solo se usan
clientes; sin esa clave, el dashboard solo permite sesiones de administrador.
