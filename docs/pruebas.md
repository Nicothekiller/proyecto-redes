# Pruebas: casos de M5 y prueba de cifrado

Todo se reproduce sobre el banco de `bench/`: 1 servidor y N clientes con WireGuard de kernel, y dependencias tomadas del flake.

```bash
CLIENTS=3 docker compose -f bench/compose.yaml up -d --build --wait
bench/mesh.sh       # malla completa
bench/cases.sh      # casos requeridos
bench/capture.sh    # tráfico cifrado frente a tráfico en claro
```

## Casos requeridos

Resultado de `bench/cases.sh` con 3 clientes:

| Caso | Resultado | Detalle |
|---|---|---|
| Join: un nodo nuevo es alcanzable | PASS | client-1 → client-3 en 2 s |
| HTTP por el overlay | PASS | `curl` a un `http.server` ligado a la IP de overlay de client-2: 200 |
| HTTP: el mismo servicio no responde por la LAN | PASS | El mismo `curl` a la IP de LAN no conecta |
| Kill: el tráfico se detiene | PASS | El ping al nodo matado falla |
| Kill: aparece offline tras ~30 s | PASS | `heartbeat_recent=false` |
| Kill: sigue registrado | PASS | La fila sigue en `/nodes`; offline no es borrado |
| Restart: el mismo `node_id` recibe la misma IP | PASS | Misma IP de overlay |
| Restart: el tráfico vuelve sin pasos manuales | PASS | En 1 s |
| Reinicio del servidor: los túneles siguen | PASS | Ping correcto durante el reinicio |
| Reinicio del servidor: IPs y nodos sobreviven | PASS | 3 nodos con sus IPs |
| Dashboard: se distingue "online con túnel caído" | PASS | Heartbeat reciente y ningún par demostrado |
| Cambio forzado de IP o puerto | Ver `docs/reconvergencia.md` | 1 s si se mueve un nodo; 11 s de mediana y 17 s de máximo si se mueven dos |

El kill se hace con `docker kill`, que equivale a apagar el equipo: desaparece la interfaz y el agente. Un `SIGTERM` (`docker stop`) también baja el túnel, porque el cliente lo baja al salir.

Otros casos cubiertos en las PRs del cliente (#25 a #29): `DELETE /nodes/{id}` quita el peer de los demás en un poll y el nodo borrado se detiene; una pubkey o endpoint malformado en `/peers` nunca llega a `wg0.conf`.

## Prueba de cifrado

`bench/capture.sh` hace que client-1 envíe 5 pings a client-2 con un payload reconocible (`overlay-proof`). Lo hace una vez por la LAN y otra por el overlay, mientras `tcpdump` escucha en `eth0` de client-2.

| Captura | ICMP visibles | UDP visibles | Payload legible |
|---|---|---|---|
| Por la LAN | 10 | 4 (probes del agente por el túnel, en paralelo) | En 10 paquetes |
| Por el overlay | 0 | 10 | En ninguno |

LAN: el ICMP se ve completo y el payload aparece en texto plano.

```text
IP 172.30.0.130 > 172.30.0.131: ICMP echo request, id 1805, seq 1, length 64
IP 172.30.0.131 > 172.30.0.130: ICMP echo reply, id 1805, seq 1, length 64
..........rlay-proofoverlay-proofoverlay-pr
```

Overlay: en el cable solo hay UDP al puerto 51820 de WireGuard. Los 64 bytes del ICMP viajan dentro de paquetes de 128 bytes cifrados, y el payload no aparece.

```text
IP 172.30.0.130.51820 > 172.30.0.131.51820: UDP, length 128
IP 172.30.0.131.51820 > 172.30.0.130.51820: UDP, length 128
```

Los 128 bytes vienen de 64 de ICMP, 20 de cabecera IP interna, 16 de cabecera de WireGuard, 16 del tag de autenticación de ChaCha20-Poly1305 y 12 de relleno a múltiplo de 16.

El script deja `bench/captures/lan.pcap` y `bench/captures/overlay.pcap` (fuera de git) para abrirlos en Wireshark y sacar las capturas de pantalla de la presentación. Wireshark los muestra como ICMP y como "WireGuard Transport Data", respectivamente.

## Límites

- Todo es en contenedores sobre un solo host. **Falta la prueba en al menos dos máquinas físicas que pide la propuesta**; la guía está en `docs/pruebas-fisicas.md`.
- Las capturas de pantalla de Wireshark no están en el repo: se sacan de los pcap.
