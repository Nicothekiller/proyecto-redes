# Test bench

One server and N clients in Docker Compose, with kernel WireGuard and every dependency taken from the repo flake (same `nix develop` environment, no `pip`).

Requirements: Docker with Compose v2 on a Linux kernel that has the `wireguard` module (native Linux, or Docker Desktop on Windows/macOS). Clients need `NET_ADMIN` and `/dev/net/tun`, not `--privileged`.

## Run

```bash
CLIENTS=3 docker compose -f bench/compose.yaml up -d --build --wait
bench/mesh.sh
```

- Each client runs `python3 -m client join --server server` on start, so `up` brings up the whole mesh with no manual step.
- `mesh.sh` pings every pair over the overlay and fails if any pair does not answer within 25 s.
- The first `--build` takes a few minutes and produces a ~3 GB image, because it builds the devshell from `flake.lock`.

On Windows, run the scripts from Git Bash.

| Setting | Default | Notes |
|---|---|---|
| `CLIENTS` | 3 | Number of client replicas |
| `API_KEY` | `benchkey` | Shared by server and clients |
| LAN | `172.30.0.0/24` | Server fixed at `172.30.0.10`. Clients take addresses from `.128/25`, so `.2`–`.127` stay free for forced IP changes |

## Scripts

| Script | What it does |
|---|---|
| `mesh.sh [limit]` | Every client reaches every other client over the overlay |
| `reconvergence.sh` | Recovery time after a forced IP or port change (issue #12). `RUNS=10` by default. Results in `docs/reconvergencia.md` |
| `overhead.sh` | RTT, throughput and CPU with vs without the tunnel, join time and agent memory (issue #16). `RUNS=5` by default. Results in `docs/overhead.md` |
| `cases.sh` | Required M5 cases: join, kill, restart, server restart, dashboard states (issue #17). Restarts client-3 and the server |
| `capture.sh` | tcpdump proof: LAN ping in clear vs overlay ping as WireGuard UDP. Leaves pcaps in `bench/captures/` (issue #17) |

`lib.sh` holds the shared helpers. `on N cmd` runs a command inside client N with the devshell environment.

## Useful commands

```bash
docker compose -f bench/compose.yaml logs -f client                 # client loops
docker stop -t 3 overlay-bench-client-2                             # SIGTERM: tunnel down, node goes offline
docker kill overlay-bench-client-2                                  # SIGKILL: crash
docker start overlay-bench-client-2                                 # same node_id, same overlay IP
docker compose -f bench/compose.yaml restart server                 # server restart, IPs persist in the server-data volume
docker compose -f bench/compose.yaml down -v                        # tear down, including the server database
```
