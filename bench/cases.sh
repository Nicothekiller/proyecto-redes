#!/usr/bin/env bash
# Required test cases from PLAN.md M5, run against the bench. Prints PASS/FAIL per case.
# Usage: bench/cases.sh   (needs the bench up with at least 3 clients; restarts client-3 and the server)

source "$(dirname "$0")/lib.sh"
set +e

failed=0
check() { # name condition-result details
  if [ "$2" = 0 ]; then echo "PASS  $1  ($3)"; else echo "FAIL  $1  ($3)"; failed=1; fi
}

node_field() { # overlay-ip field
  api /nodes | on_server python3 -c "
import json, sys
for n in json.load(sys.stdin):
    if n['overlay_ip'] == sys.argv[1]:
        print(n[sys.argv[2]])
" "$1" "$2" | tr -d '\r'
}

C3=overlay-bench-client-3
A=$(overlay_ip 1)
C=$(overlay_ip 3)

t=$(wait_ping 1 "$C" 25); check "join: new node reachable" $? "client-1 -> client-3 after $t s"

docker kill "$C3" >/dev/null
sleep 2
on 1 ping -c 1 -W 1 "$C" >/dev/null 2>&1; [ $? != 0 ]; check "kill: traffic stops" $? "ping to $C fails"
sleep 33
[ "$(node_field "$C" heartbeat_recent)" = False ]; check "kill: shown offline after ~30 s" $? "heartbeat_recent=$(node_field "$C" heartbeat_recent)"
[ -n "$(node_field "$C" overlay_ip)" ]; check "kill: still registered" $? "row kept in /nodes"

docker start "$C3" >/dev/null
sleep 3
[ "$(overlay_ip 3)" = "$C" ]; check "restart: same node_id gets same IP" $? "$(overlay_ip 3)"
t=$(wait_ping 1 "$C" 25); check "restart: traffic back without manual steps" $? "after $t s"

dc restart server >/dev/null 2>&1
on 1 ping -c 1 -W 1 "$C" >/dev/null 2>&1; check "server restart: tunnels keep working" $? "ping during restart"
sleep 12
[ "$(node_field "$A" heartbeat_recent)" = True ] && [ "$(node_field "$C" overlay_ip)" = "$C" ]
check "server restart: IPs and nodes survive" $? "$(api /nodes | on_server python3 -c 'import json,sys; print(len(json.load(sys.stdin)), "nodes")' | tr -d '\r')"

on 1 ip link set wg0 down
sleep 22
[ "$(node_field "$A" heartbeat_recent)" = True ]; r1=$?
api /status | on_server python3 -c "
import json, sys
pairs = [p for p in json.load(sys.stdin)['pairs'] if sys.argv[1] in (p['reporter_overlay_ip'], p['peer_overlay_ip'])]
sys.exit(0 if pairs and not any(p['connectivity_proven'] for p in pairs) else 1)
" "$A"
r2=$?
[ $r1 = 0 ] && [ $r2 = 0 ]; check "dashboard: online but tunnel down is told apart" $? "heartbeat recent, no proven pair"
on 1 ip link set wg0 up
docker restart -t 3 overlay-bench-client-1 >/dev/null
sleep 3

echo "endpoint change: see bench/reconvergence.sh and docs/reconvergencia.md"
exit "$failed"
