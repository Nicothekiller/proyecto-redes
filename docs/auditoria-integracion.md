# Auditoría de integración servidor / cliente

Revisión de `master` en `54f8205` hecha mientras se escribía el cliente (M2 y M3). Cubre lo que el cliente necesita del servidor y lo que falta para la defensa.

**Se ejecutó** en contenedores Python 3.13: pytest, ruff, ty, uvicorn real con curl y un banco con WireGuard de kernel (1 servidor, 3 clientes).
**No se ejecutó** bajo `nix develop` con el lockfile del flake, ni en máquinas físicas.

## Veredicto

- El servidor funciona y cumple el contrato con el cliente: IPs estables, persistencia tras reinicio, delete, 409, 401 y joins concurrentes sin colisión.
- **El dashboard (#15) no existe en ninguna rama.** La API alcanza para construirlo, pero falta decidir cómo se autentica el navegador. Sin él no se cumple el M4 ni el requisito de las tres columnas.

## Hallazgos del servidor

| # | Severidad | Hallazgo | Estado |
|---|---|---|---|
| N1 | Alta | Endpoint y pubkey sin validar: un salto de línea llega al `wg0.conf` de los demás nodos y `wg-quick` ejecuta `PostUp` como root | PR de fix aparte |
| N2 | Alta | Un heartbeat que reporta un peer recién borrado da 404 y hace rollback completo, incluido `last_heartbeat` | PR de fix aparte |
| N3 | Media | `register` con un `node_id` existente y otra pubkey se acepta y conserva la IP: quien tenga la key toma la IP de otro nodo. Contradice "no key rotation" (`PLAN.md`) | Decisión de Nico: 409 o declararlo |
| N4 | Baja | `Authorization: Bearer ñandú` da 500, `compare_digest` no acepta no ASCII (`server/auth.py`). Fix: comparar bytes | Pendiente |
| N5 | Baja | `database is locked`: 2 de 3000 heartbeats con 64 hilos. Irrelevante con pocos nodos | Pendiente |
| N6 | Baja | `--workers 4` da 500 por `UNIQUE overlay_ip`: el lock es por proceso. Sin IPs duplicadas | Declarar: un solo worker |
| N7 | Baja | `rx_bytes = 2**64` da 500 por overflow. Fix: `le=2**63-1` | Pendiente |
| N8 | Baja | `handshake_age_s` negativo si el reloj del cliente va adelantado. Fix: `max(0, ...)` y NTP | Pendiente |
| N9 | Baja | `main.py` sigue diciendo M1b; `/peers` y `/nodes` ordenan lexicográfico (.10 antes de .2); `DATABASE_URL` relativo al cwd | Pendiente |

## Lo que falta para el dashboard (#15)

| Punto | Situación | Propuesta |
|---|---|---|
| Auth del navegador | La misma key registra y borra nodos, no puede ir en el HTML | `DASHBOARD_KEY` de solo lectura para `GET /nodes` y `/status`, o pedirla en pantalla y guardarla solo en memoria |
| Servir la UI | No hay rutas ni estáticos; `/nodes` ya es JSON | Montarla en el mismo FastAPI, en `/dashboard`. Así no hace falta CORS |
| Estado por nodo | `connectivity_proven` usa `any()`: en el banco, con el túnel a-b bloqueado, a y b siguen saliendo proven por su par con c | Mostrar la verdad por par y rotular la de nodo como "al menos un par" |
| Datos viejos | Si un reportero cae, `/status` sigue mostrando su último `probe_ok`, rtt y rx/tx; `reported_at` no se expone | Agregar `reported_at` a `PairOut` y atenuar esas filas |
| Peer count, delta rx/tx, pubkey truncada | No están en la API; un test exige la ausencia de `peer_count` | Calcularlos en la UI, tolerando reinicio de contadores |
| Pares sin reporte | Ausentes, no nulos | Mostrar "sin datos", no "caído" |

## Comprobado con WireGuard real

| Estado | `heartbeat_recent` | `connectivity_proven` del par | Cómo se forzó |
|---|---|---|---|
| Conectado y demostrado | sí | sí | 3 clientes en régimen; 35 muestras seguidas sin parpadeo con poll 10 s y TTL 15 s |
| Online con túnel caído | sí | no | UDP bloqueado entre a y b con nftables, API accesible |
| Registrado y offline | no | no | Cliente c matado con SIGKILL, `age` llega a 37 s |

También se capturó el tráfico hacia la API con tcpdump: 45 heartbeats, 0 apariciones de las llaves privadas de los 3 nodos en tráfico y logs del servidor, y las llaves públicas sí aparecen, lo que confirma que la búsqueda funcionaba.

## Preguntas de defensa

| Pregunta | Respuesta |
|---|---|
| ¿Cómo evitan dos nodos con la misma IP? | Lock, transacción y `UNIQUE` en BD. Con varios workers el lock no sirve y responde el `UNIQUE` con un 500, por eso se corre con uno |
| ¿Por qué hard delete y no flag? ¿Y la cuarentena del #11? | M3 reemplazó el flag: modelo simple, pool sin fugas. Costo: una IP reutilizada puede apuntar un momento a otra pubkey en clientes sin actualizar. El cliente quita antes de agregar para acotarlo |
| ¿Qué demuestra `connectivity_proven`? | Un ping real por el overlay dentro de `PROBE_TTL_S`. Handshake y contadores no cuentan |
| ¿Qué pasa si el servidor cae? | Nada en el plano de datos: los túneles siguen. Comprobado en el banco. Al volver, SQLite conserva IPs y peers |
| ¿Por qué la llave privada nunca sale? | Se genera en el cliente, viaja a `wg` por stdin y no por argv, y el heartbeat es una lista cerrada de campos; además el servidor prohíbe campos extra |
| ¿Seguridad de la API? | Bearer compartido en tiempo constante, sin TLS y sin roles. Alcance de prototipo. Tener claro N3 |
| ¿Por qué polling? | Simplicidad acordada; costo: convergencia ligada al intervalo. Ver `docs/reconvergencia.md` |
