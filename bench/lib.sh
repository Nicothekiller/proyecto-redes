#!/usr/bin/env bash
# Helpers shared by the bench scripts. Client N is the Nth replica of the client service.

set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "${BASH_SOURCE[0]}")"

API_KEY=${API_KEY:-benchkey}
SERVER=172.30.0.10

dc() { docker compose "$@"; }
on() { local n=$1; shift; dc exec -T --index "$n" client /devshell "$@"; }
on_server() { dc exec -T server /devshell "$@"; }
clients() { dc ps -q client | wc -l | tr -d ' '; }

state() { on "$1" python3 -c "import json; print(json.load(open('/var/lib/overlay-client/state.json'))['$2'])" | tr -d '\r'; }
overlay_ip() { state "$1" overlay_ip; }
lan_ip() { on "$1" sh -c "ip -4 -o addr show eth0 | awk '{print \$4}' | cut -d/ -f1" | tr -d '\r'; }

api() { on_server curl -s -H "Authorization: Bearer $API_KEY" "http://127.0.0.1:8000$1"; }

wait_ping() { # from-client target limit-seconds
  local i
  for i in $(seq 1 "$3"); do
    on "$1" ping -c 1 -W 1 "$2" >/dev/null 2>&1 && { echo "$i"; return 0; }
    sleep 1
  done
  echo "TIMEOUT"
  return 1
}
