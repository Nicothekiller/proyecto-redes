#!/usr/bin/env bash
# Measures recovery time after a forced endpoint change (issue #12).
# The change and the measurement start at the same absolute instant T, taken from the
# containers' shared clock; the result is T -> first ping of 5 consecutive ones.
# Runs are spaced randomly so T lands at a random phase of the poll.
# Usage: RUNS=10 bench/reconvergence.sh   (needs the bench up with at least 2 clients)

source "$(dirname "$0")/lib.sh"

RUNS=${RUNS:-10}
A=$(overlay_ip 1)
B=$(overlay_ip 2)
echo "client-1=$A client-2=$B runs=$RUNS"
wait_ping 1 "$B" 25 >/dev/null

instant() { on_server python3 -c "import time; print(round(time.time() + 2.5, 3))" | tr -d '\r'; }

change_at() { # client T shell-command
  dc exec -d -T --index "$1" client /devshell python3 -c "
import subprocess, sys, time
time.sleep(max(0, float(sys.argv[1]) - time.time()))
subprocess.run(['sh', '-c', sys.argv[2]], check=True)
" "$2" "$3"
}

measure_at() { # client T target
  on "$1" python3 -c "
import subprocess, sys, time
t0, target = float(sys.argv[1]), sys.argv[2]
time.sleep(max(0, t0 - time.time()) + 0.05)
first = None
ok = 0
while time.time() - t0 < 40:
    t = time.time()
    if subprocess.run(['ping', '-c', '1', '-W', '1', target], capture_output=True).returncode == 0:
        first = first or t
        ok += 1
        if ok == 5:
            break
        time.sleep(0.2)
    else:
        first = None
        ok = 0
print('%.2f' % (first - t0) if ok == 5 else 'TIMEOUT')
" "$2" "$3" | tr -d '\r'
}

summary() {
  on_server python3 -c "
import statistics as s, sys
v = [float(x) for x in sys.argv[2:] if x != 'TIMEOUT']
print('%s: n=%d mean=%.2fs median=%.2fs min=%.2fs max=%.2fs timeouts=%d'
      % (sys.argv[1], len(v), s.mean(v), s.median(v), min(v), max(v), len(sys.argv) - 2 - len(v)))
" "$@"
}

move() { echo "ip addr flush dev eth0 && ip addr add $1/24 dev eth0"; }

run_case() { # name body-function
  local results=() v i
  echo "=== $1"
  for i in $(seq 1 "$RUNS"); do
    sleep $((RANDOM % 10 + 3))
    v=$("$2" "$i")
    results+=("$v")
    printf '%s ' "$v"
  done
  echo
  summary "$1" "${results[@]}"
}

one_moves() { local t; t=$(instant); change_at 1 "$t" "$(move "172.30.0.$((20 + $1))")"; measure_at 2 "$t" "$A"; }
both_move() {
  local t; t=$(instant)
  change_at 2 "$t" "$(move "172.30.0.$((50 + $1))")"
  change_at 1 "$t" "$(move "172.30.0.$((80 + $1))")"
  measure_at 1 "$t" "$B"
}
port_moves() { local t; t=$(instant); change_at 1 "$t" "wg set wg0 listen-port $((52000 + $1))"; measure_at 2 "$t" "$A"; }

run_case "one-moves (client-1 changes IP, client-2 pings it)" one_moves
run_case "both-move (both change IP at once, client-1 pings client-2)" both_move
run_case "port-moves (client-1 changes listen port, client-2 pings it)" port_moves
