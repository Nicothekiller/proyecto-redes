# Guía de prueba en máquinas físicas

La propuesta pide pruebas en al menos dos máquinas físicas además del banco Docker. Esta guía repite en un hotspot real los casos y las mediciones de `docs/pruebas.md`, `docs/overhead.md` y `docs/reconvergencia.md`, para poder comparar.

## Requisitos

- **Equipos:** 2 o más PCs con Linux nativo. WSL2 no sirve, porque normalmente no tiene el módulo `wireguard` (`PLAN.md`, M0).
- **Software:** nix con flakes y `sudo` en todos los equipos.
- **Red:** un hotspot propio, por ejemplo el del celular, con todos los equipos en el mismo segmento.
- **Wireshark:** en al menos un equipo, para las capturas de pantalla.

Roles con dos equipos: **PC-A** corre el servidor y un cliente, **PC-B** corre otro cliente. Con un tercer equipo, el servidor puede ir solo en él, como en la propuesta.

## 0. Preparación (en cada PC)

```bash
git clone https://github.com/Nicothekiller/proyecto-redes.git && cd proyecto-redes
nix develop
ip -4 addr                     # anota la IP del hotspot y la interfaz (wlan0, wlp2s0...)
ip route | grep 10.100.0       # no debe salir nada: el overlay no puede chocar con otra red
```

Comprueba que el hotspot no aísla a los clientes. En PC-A ejecuta `nc -u -l 51820`; en PC-B, `echo hola | nc -u <IP-A> 51820`. Si no llega, el hotspot aísla clientes: cambia de hotspot. Si hay firewall, abre UDP 51820 en todos los equipos y TCP 8000 en PC-A.

**Dentro de `nix develop`, usa siempre `sudo env "PATH=$PATH" ...`.** Con `sudo` a secas se ejecuta el Python del sistema y no el del flake.

## 1. Levantar la red

PC-A, servidor. La base de datos va con ruta absoluta, para que no cambie si lo arrancas desde otra carpeta:

```bash
API_KEY=<key> DATABASE_URL=sqlite:///$PWD/overlay.db uvicorn server.main:app --host 0.0.0.0 --port 8000
```

En cada PC (en PC-A, en otra terminal):

```bash
sudo env "PATH=$PATH" python3 -m client join --server <IP-A> --key <key>
```

Las IPs de overlay quedan en los logs (`joined as ... with overlay ip 10.100.0.x`). El estado se ve con:

```bash
curl -s -H "Authorization: Bearer <key>" http://<IP-A>:8000/nodes | python3 -m json.tool
```

## 2. Casos

| Caso | Cómo | Qué esperar |
|---|---|---|
| Conectividad | Desde cada PC, `ping <IP-overlay-del-otro>` | Responde en ambos sentidos |
| HTTP por el overlay | PC-B: `python3 -m http.server 8080 --bind <overlay-B>`. PC-A: `curl http://<overlay-B>:8080/` y `curl http://<IP-B>:8080/` | Responde por el overlay; por la LAN falla |
| Kill | PC-B: `sudo pkill -9 -f "client join"` y luego `sudo wg-quick down /var/lib/overlay-client/wg0.conf` | El ping a B se corta; a los ~30 s `/nodes` muestra `heartbeat_recent: false` y B sigue registrado |
| Regreso | PC-B: el mismo comando `join` | Misma IP de overlay; el ping vuelve sin pasos manuales |
| Reinicio del servidor | PC-A: Ctrl+C a uvicorn y arrancarlo de nuevo | El ping entre clientes no se corta; `/nodes` conserva nodos e IPs |
| Online con túnel caído | PC-B: `sudo ip link set wg0 down` | Tras ~20 s, B sigue con heartbeat reciente pero ningún par con B sale `connectivity_proven` en `/status` |

## 3. Mediciones

**Latencia** (5 repeticiones de cada una, intercaladas). Anota el valor `avg`:

```bash
ping -q -c 50 -i 0.2 <IP-B>          # sin túnel
ping -q -c 50 -i 0.2 <overlay-B>     # con túnel
```

**Throughput** (5 repeticiones de cada uno). En PC-B, `iperf3 -s`. En PC-A:

```bash
iperf3 -c <IP-B> -t 10          # sin túnel
iperf3 -c <overlay-B> -t 10     # con túnel
```

Para la CPU, lee `head -1 /proc/stat` justo antes y justo después de cada iperf3. Las columnas son user, nice, system, idle, iowait, irq, softirq...; el cifrado aparece en softirq.

**Join**: en PC-B, con la red ya levantada y B fuera de ella:

```bash
t0=$(date +%s.%N); sudo env "PATH=$PATH" python3 -m client join --server <IP-A> --key <key> > client.log 2>&1 &
until ping -c 1 -W 1 <overlay-A> > /dev/null 2>&1; do :; done; echo "$(date +%s.%N) - $t0" | python3 -c "print(round(eval(input()), 2))"
```

Para medirlo varias veces sin que cambie la IP, deja el agente con Ctrl+C (baja el túnel) y repite.

**Reconvergencia**: deja `ping <overlay-B>` corriendo en PC-A y fuerza un cambio en PC-B. Anota cuántos segundos se pierden.

| Cambio | Comando en PC-B |
|---|---|
| Puerto | `sudo wg set wg0 listen-port 52001` (usa uno distinto en cada repetición) |
| IP | Fija otra IP del hotspot: `nmcli con mod <red> ipv4.method manual ipv4.addresses <IP-nueva>/24 ipv4.gateway <gateway> && nmcli con up <red>` |

El caso más exigente es que ambos PCs cambien de IP a la vez, porque ahí el roaming de WireGuard no ayuda y depende del servidor (`docs/reconvergencia.md`).

## 4. Captura para Wireshark

En PC-B:

```bash
sudo tcpdump -i <interfaz> -w lan.pcap 'host <IP-A>'        # Ctrl+C tras el ping
sudo tcpdump -i <interfaz> -w overlay.pcap 'host <IP-A>'
```

Mientras captura, desde PC-A, con un payload reconocible:

```bash
ping -c 5 -p 6f7665726c61792d70726f6f66 <IP-B>          # para lan.pcap
ping -c 5 -p 6f7665726c61792d70726f6f66 <overlay-B>     # para overlay.pcap
```

Abre ambos en Wireshark y saca las capturas de pantalla:
- **`lan.pcap`:** ICMP con `overlay-proof` legible en los bytes.
- **`overlay.pcap`:** solo "WireGuard Transport Data" por UDP 51820, sin el texto.

## 5. Registro de resultados

Completa esta tabla y pásala a `docs/pruebas.md` junto a los resultados del banco:

| Medida | Banco Docker | Físico: media | Físico: mín | Físico: máx |
|---|---|---|---|---|
| RTT sin túnel (ms) | 0,095 | | | |
| RTT con túnel (ms) | 0,598 | | | |
| Throughput sin túnel (Mbit/s) | 30 285 (veth, no representativo) | | | |
| Throughput con túnel (Mbit/s) | 594 | | | |
| Join hasta alcanzar a otro nodo (s) | 7,1 | | | |
| Reconvergencia, cambio de puerto (s) | 1,06 | | | |
| Reconvergencia, cambio de IP (s) | 1,05 | | | |

Anota también el modelo de los equipos, el hotspot usado y la fecha.
