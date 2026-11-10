# proyecto-redes

Servidor de coordinación mínimo para WireGuard, al estilo de un Headscale reducido. Un servidor reparte IPs de overlay (`10.100.0.0/24`) y la lista de peers. Cada cliente genera sus llaves, se registra, levanta `wg0` y mantiene la malla al día por polling. El tráfico entre nodos va directo y cifrado por WireGuard: el servidor solo coordina.

Alcance: una LAN, un servidor y unos pocos clientes Linux. Sin relay, sin NAT traversal, sin multiusuario ni ACLs. El plan completo y las decisiones están en `PLAN.md`.

## Cómo funciona

| Plano | Qué viaja | Por dónde |
|---|---|---|
| Control | Registro, heartbeats, lista de peers, estadísticas | HTTP al servidor, con Bearer |
| Datos | Tráfico entre nodos | UDP 51820 directo entre nodos, cifrado por WireGuard |

Si el servidor cae, los túneles siguen funcionando. Lo único que se pausa es la incorporación de cambios.

- **Servidor** (`server/`): FastAPI y SQLite en modo WAL. `POST /register`, `GET /peers`, `POST /heartbeat`, `DELETE /nodes/{id}`, y para el dashboard `GET /nodes` y `GET /status`.
- **Cliente** (`client/`): `join` genera el par de llaves en local (la privada nunca sale del equipo), escribe `wg0.conf` y lo levanta. Cada 10 s envía heartbeat con estadísticas y un ping de prueba por peer, y aplica solo los cambios de `/peers` con `wg set`. Un cambio de IP o puerto se reporta en menos de 1 s.

## Uso

Todo dentro del devshell de nix:

```bash
nix develop
API_KEY=<key> uvicorn server.main:app --host 0.0.0.0 --port 8000      # servidor
sudo env "PATH=$PATH" python3 -m client join --server <IP-del-servidor> --key <key>   # cada cliente
```

Para probar sin varias máquinas, el banco de `bench/` levanta 1 servidor y N clientes en Docker con WireGuard de kernel:

```bash
CLIENTS=3 docker compose -f bench/compose.yaml up -d --build --wait
bench/mesh.sh
```

Detalles en `bench/README.md`. Las verificaciones de código (`ruff`, `ty`, `pytest`) están en `AGENTS.md`.

## Resultados

| Documento | Contenido |
|---|---|
| `docs/pruebas.md` | Casos requeridos (join, HTTP, caída, regreso, reinicio del servidor, estados del dashboard) y prueba de cifrado con tcpdump |
| `docs/pruebas-fisicas.md` | Guía para repetir casos, mediciones y captura en dos o más PCs en un hotspot |
| `docs/reconvergencia.md` | Tiempo de recuperación ante cambio de IP o puerto: ~1 s si se mueve un nodo, ≤ 17 s si se mueven dos |
| `docs/overhead.md` | RTT, throughput y CPU con y sin túnel, tiempo de join y memoria del agente |
| `docs/auditoria-integracion.md` | Revisión del servidor frente al cliente, pendientes y preguntas de defensa |

## Estado

| Hito | Estado |
|---|---|
| M0 a M3: servidor, cliente, persistencia, reconvergencia | Hecho |
| M4: API del dashboard | Hecho |
| M4: interfaz del dashboard (#15) | En curso |
| M5: banco, mediciones, prueba de cifrado y documentación | Hecho en el banco Docker; falta la prueba en máquinas físicas (`docs/pruebas-fisicas.md`) |
| M6: relay (#18) | Fuera de alcance |
