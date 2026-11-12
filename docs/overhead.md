# Overhead del túnel

Mismo par de clientes, misma carga y misma duración, primero por la LAN (sin túnel) y luego por el overlay, intercalados. 5 repeticiones de cada uno. Se reproduce con `RUNS=5 bench/overhead.sh` sobre el banco de `bench/`.

## Resultados

| Métrica | LAN: media | LAN: mín | LAN: máx | Overlay: media | Overlay: mín | Overlay: máx |
|---|---|---|---|---|---|---|
| RTT, 50 pings cada 0,2 s (ms) | 0,095 | 0,081 | 0,110 | 0,598 | 0,547 | 0,663 |
| Throughput, iperf3 TCP 10 s (Mbit/s) | 30 285 | 28 313 | 31 595 | 594 | 563 | 644 |
| CPU ocupada del sistema durante iperf3 (%) | 23,1 | 22,8 | 23,6 | 42,3 | 41,9 | 42,6 |
| CPU en softirq durante iperf3 (%) | 8,7 | 8,6 | 9,2 | 23,2 | 23,0 | 23,4 |

La CPU es del sistema completo (8 CPUs), no solo de iperf3, porque el cifrado de WireGuard corre en el kernel, en softirq.

| Otras medidas | Media | Mín | Máx |
|---|---|---|---|
| Join: el nodo nuevo alcanza a uno existente (s) | 7,08 | 6,34 | 7,83 |
| Join: un nodo existente alcanza al nuevo (s) | 7,81 | 6,96 | 8,52 |
| Memoria del agente cliente, VmRSS (MB) | ~33 | 32,9 | 33,4 |

Los tiempos de reconvergencia ante cambio de IP o puerto están en `docs/reconvergencia.md`.

## Cómo leerlo

**Latencia.** El túnel suma ~0,5 ms por ida y vuelta: cifrar, descifrar y pasar por la interfaz `wg0`. En una LAN o hotspot real, donde el RTT base es de 1 a 10 ms, eso es poco.

**Throughput.** La "LAN" del banco es un par veth dentro de la misma máquina virtual: copiar memoria da 30 Gbit/s, algo que ninguna red física entrega. La cifra útil es la del overlay: un flujo TCP cifrado llegó a ~600 Mbit/s en este equipo. En el hotspot o en Ethernet de 1 Gbit/s, el límite pasa a ser el enlace y no WireGuard. Hay que repetirlo en las máquinas físicas para tener la comparación real.

**Costo de CPU.** Por bit transmitido, el overlay cuesta mucho más: casi el doble de CPU total para la cincuentava parte del tráfico. La diferencia se concentra en softirq, que pasa de 8,7 % a 23,2 %, donde el kernel cifra.

**Memoria.** El agente cliente ocupa ~33 MB por nodo, casi todo del intérprete de Python y sus librerías. La memoria de WireGuard en el kernel no está incluida.

**Join.** El tiempo incluye crear y arrancar el contenedor. Los dos sentidos dan casi lo mismo porque ambos esperan al mismo evento: WireGuard rechaza handshakes de llaves que no conoce, así que ni siquiera el nodo nuevo llega hasta que el existente agrega su llave en su siguiente poll. Por eso queda acotado por arranque del contenedor más hasta un poll (10 s).

## Límites

- Todo corre en un solo host: no hay pérdida, ni latencia, ni límite de ancho de banda de una red real.
- Es un solo flujo TCP. Con varios flujos en paralelo el overlay podría repartir el cifrado entre más CPUs.
- La CPU de softirq incluye todo lo que hizo el kernel en ese intervalo, no solo el cifrado.
