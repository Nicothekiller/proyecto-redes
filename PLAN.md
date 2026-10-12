# Plan - Minimal WireGuard Coordination Server (Headscale-lite)

Base: `Prpuesto Proyecto Redes.pdf` + teacher notes.
Scope: 1 LAN, 1 server + 2-3 Linux clients, overlay `10.100.0.0/24` (verify no collision first).
No relay, no NAT traversal, no multi-user, no ACLs.

Stack: Python (FastAPI or Flask), SQLite later, REST + polling, read-only dashboard (same API).
Test env: native Linux PCs + Docker Compose later.
Deps via `nix` everywhere so Ubuntu and NixOS behave the same.

Order: simplest presentable first. Complicated parts pushed to end.

## Ownership

* **Nic: server** — M0 env, M1a in-memory API, M1b SQLite persistence, M3 server hardening, M4 dashboard backend + UI, shared M5/M6.
* **Teammate (Felipe): client** — starts once M1a `POST /register, GET /peers, POST /heartbeat` works with `curl`. Owns M2 client (join, wg apply, poll loop, stats filtering), M3 client reconvergence, helps M5 measurements + docs.
* Handoff contract (frozen after M1a): request/response fields for register/peers/heartbeat + Bearer auth + `AllowedIPs = <peer_overlay>/32` rule. Server changes must not break it without telling client side.
* Both must be able to explain all code in final presentation.

---

## 0. Dependencies via nix flake

Install nix once on Ubuntu teammate machine. NixOS already has it.

```bash
# Ubuntu teammate, one time:
sh <(curl -L https://nixos.org/nix/install) --daemon
# then enable flakes (if not already): add `experimental-features = nix-command flakes` to /etc/nix/nix.conf
```

Use the repo flake for everything. No hand-rolled `nix-shell -p`, no `pip install`:

```bash
nix develop
python3 --version
wg --version
ip -V
```

All deps (python + fastapi/uvicorn/requests/pytest + wireguard-tools, iproute2, iputils, iperf3, curl, sqlite, tcpdump, netcat) come from `flake.nix`.

---

## M0: Env check (do first, ~hours)

Goal: prove WireGuard works on your real machines before writing coordination logic.

1. Tools present: enter `nix develop`, then `wg`, `ip`, `python3` are there.
2. Can create interfaces (needs root / CAP_NET_ADMIN):
   ```bash
   sudo ip link add wg0 type wireguard
   sudo ip link del wg0
   ```
   In Docker later needs `cap_add: [NET_ADMIN, SYS_MODULE]` + `/dev/net/tun`. On WSL2 this often fails (no wg kernel module) -> prefer native Linux for real tests, use `wireguard-go` fallback only if forced.
3. UDP reachability on your LAN/hotspot (inside `nix develop`):
   ```bash
   # PC-A:
   nc -u -l 51820
   # PC-B:
   echo hi | nc -u <PC-A-LAN-IP> 51820
   ```
   If hotspot isolates clients, switch to phone hotspot or test via Docker bridge.
4. Subnet collision:
   ```bash
   ip route
   ```
   If `10.100.0.0/24` overlaps, freeze a new one now (e.g. `10.200.0.0/24`). Don't change mid-project.
5. `wg show` privacy rule: **never send raw `wg show dump` to server** (contains private + preshared keys). Plan is to read `latest-handshakes`, `endpoints`, `transfer` separately, or filter locally before POST. See `man wg.8`.

Exit M0 when: manually configured `wg` with static keys pings between 2 native machines.

---

## M1: Server v0 - in-memory first, DB afterwards

Build server before client. Test with `curl` + manual `wg`, no automation yet.

### M1a: in-memory (this week)

Single Python process, dicts only, no SQLite yet. Data is lost on restart - expected for now.

State:
```
nodes: dict[node_id -> {pubkey, overlay_ip, endpoint, last_heartbeat, deleted}]
pubkey_index: dict[pubkey -> node_id]
ip_pool: next free host in 10.100.0.0/24, start .2 (.1 reserved), free list for reuse
API_KEY: from env var, `Authorization: Bearer <key>`
```

API v0:
* `POST /register` in `{node_id, pubkey, endpoint}` + Bearer auth -> out `{overlay_ip, peers[]}`.
  If `node_id` known and not deleted: return same `overlay_ip` (stable identity).
  Else: allocate next free IP under a lock (avoid double-assign on simultaneous joins), store, return it.
* `GET /peers?node_id=...` + Bearer auth -> `[{node_id, overlay_ip, pubkey, endpoint}]` for all non-deleted nodes except requester.
* `POST /heartbeat` in `{node_id, endpoint?}` -> update `last_heartbeat`, update endpoint if changed.

Rules v0:
* `AllowedIPs` concept: each `overlay_ip` maps 1:1 to one `pubkey`/`endpoint`. Server just distributes the list, client writes `AllowedIPs = <peer_overlay>/32`.
* Private key never sent to server.
* Use a threading Lock around allocate/register for now (DB transaction comes in M3).
* Offline timeout not enforced yet (just record `last_heartbeat`).

Test M1a: `curl` register A + B, hand-write two `wg0.conf`, `ping 10.100.0.x` works. This is first demoable cut.

### M1b: add persistence (after M1a works)

Swap dicts for SQLite (WAL mode), same API. Add UNIQUE on `node_id, pubkey, overlay_ip`. Allocation inside a transaction. Server restart keeps same IPs. Add `deleted` flag to separate offline-temporary vs removed.

---

## M2: Client v0 (after server v0 works)

One-command join, Linux only, needs sudo + `wireguard-tools`.

Steps:
1. First `join --server <IP> --key <API_KEY>`: `wg genkey | wg pubkey`, uuid `node_id`, save to `state.json` + `privatekey` (0600). Reuse on reboot -> same IP.
2. Detect endpoint: LAN IP + listen-port (default `51820`). POST `/register`.
3. Save `overlay_ip`. Render `wg0.conf`: `[Interface] PrivateKey, Address=overlay/24, ListenPort` + one `[Peer]` per `/peers` entry with `PublicKey, Endpoint, AllowedIPs=<overlay>/32, PersistentKeepalive=25`.
4. Apply via `wg-quick up` or `ip link + wg setconf`.
5. Poll loop every ~10s: `POST /heartbeat` + `GET /peers`. On change, apply deltas with `wg set` / `syncconf`, don't wipe keys or restart all tunnels.
6. Stats reporting (local filter first): only send handshake time, endpoint, rx/tx per peer. No private/preshared keys in logs or dashboard.

Test: fresh `join` -> pingable within polling interval + handshake. Restart keeps IP.

---

## M3: Hardening + reconvergence (after M1b + M2 work)

Owner: Nic (server) + Felipe (client). Needs both sides.

Server (Nic):
* Offline rule: `now - last_heartbeat > 30s` -> `offline`. Keep entry. Explicit `POST /delete` or `DELETE /nodes/:id` -> `deleted=true`, excluded from `/peers`, IP quarantined (don't reassign immediately).
* Concurrency: allocation in one transaction / lock. Simultaneous joins never get same IP. Same `node_id` re-register returns same IP; new `node_id` with duplicate `pubkey` rejected.
* Peer updates preserve keys: `/peers` output is deterministic order, includes only non-deleted nodes. No key rotation here.
* `AllowedIPs` stays 1:1 `overlay_ip/32 -> pubkey`. Server never emits overlapping ranges.

Client (Felipe):
* Poll every ~10s: `POST /heartbeat {node_id, endpoint}` + `GET /peers`. Detect local endpoint change (LAN IP or port changed) and report it immediately.
* Apply only deltas with `wg set` / `wg syncconf`: add new peers, update changed endpoints, remove deleted peers. Don't wipe private key or flap healthy tunnels.
* Stats filter: parse `wg show <iface> latest-handshakes/endpoints/transfer` separately (or filter `dump` locally). POST only `{peer_pubkey_truncated?, overlay_ip, endpoint, last_handshake, rx, tx}`. Never send private/preshared keys, never log them.

Done when: kill client -> shows offline after ~30s, traffic stops; restart same `node_id` -> same IP back, traffic resumes without manual steps. Forced endpoint change (change LAN IP / port explicitly, not just container restart) propagates within ~2 poll intervals.

## M4: Dashboard - observability (read-only)

Owner: Nic (serves UI + API), Felipe reviews against client behavior.

* Same REST API the clients use, plus read endpoints for UI: `GET /nodes`, `GET /status`. No control actions except maybe `Ping now` trigger.
* Three separate columns, never merged (teacher requirement):
  1. `registered` - in DB, not deleted.
  2. `heartbeat recent` - `last_heartbeat < 30s ago`.
  3. `connectivity proven` - result + timestamp of last active probe (ping over overlay or fresh handshake delta). Old handshake age or cumulative byte counters alone do NOT count.
* Per node: overlay IP, truncated pubkey (`abcd...wxyz`), endpoint, last heartbeat age, peer count.
* Per pair: last handshake age, rx/tx (and delta since last poll), endpoint used.
* Auto-refresh every few seconds. Show `as of <timestamp>` and `probe ran at <timestamp>`.
* No secrets in UI, logs, or API responses.

Done when: you can tell apart registered-but-offline vs online-but-tunnel-down vs proven-connected, with timestamps.

## M5: Test bench + measurements + docs

Owners: both. Needs Docker Compose + 2+ physical machines on same hotspot.

* Compose bench: 1 server + N clients (configurable count), `NET_ADMIN + /dev/net/tun`, fixed LAN subnet for reproducibility. Physical test: same hotspot, same binaries.
* Required cases: join new node -> reachable; kill client -> offline; restart same ID -> same IP + traffic back; forced endpoint/IP change -> reconvergence time measured (change moment -> stable ping again, contrast with poll interval); server restart -> IPs + peers survive (after M1b).
* Overhead comparison: ping + iperf3 with vs without tunnel. Same nodes, same load, same duration, 5+ repeats each, record mean/min/max + CPU/mem if relevant.
* Wireshark/tcpdump proof: overlay ping shows UDP WireGuard ciphertext; baseline ping shows ICMP in clear.
* Docs: table of results, screenshots, how to reproduce (`nix develop` + compose up + join commands).

## M6: Out of scope / only if time

Relay/TURN, NAT hole punching, multi-user/OIDC, ACLs, key rotation, Windows/macOS/mobile clients. Relay explicitly not needed for the proposal.

Suggested: 2w M0+M1, 3w M2+M3, 1w M5 tests, 2w M4 dashboard + docs.

This week: M0 checks + M1a in-memory `POST /register, GET /peers, POST /heartbeat` (Nic). Felipe on standby until curl demo passes, then M2 starts.
