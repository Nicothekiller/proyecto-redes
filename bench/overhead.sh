#!/usr/bin/env bash
# Tunnel overhead (issue #16): the same pair of clients, the same load and duration,
# once over the LAN (no tunnel) and once over the overlay, alternating, RUNS times each.
# Also measures join time of a new client and the memory of the client agent.
# Usage: RUNS=5 bench/overhead.sh   (needs the bench up with at least 2 clients)

source "$(dirname "$0")/lib.sh"

RUNS=${RUNS:-5}
PINGS=${PINGS:-50}
IPERF_S=${IPERF_S:-10}

LAN_B=$(lan_ip 2)
OVL_B=$(overlay_ip 2)
OVL_A=$(overlay_ip 1)
echo "client-1 -> client-2: lan=$LAN_B overlay=$OVL_B runs=$RUNS pings=$PINGS iperf=${IPERF_S}s"
wait_ping 1 "$OVL_B" 25 >/dev/null

on 2 sh -c 'iperf3 -s -D >/dev/null 2>&1 || true'
sleep 1

rtt() { # target -> avg rtt ms
  on 1 ping -q -c "$PINGS" -i 0.2 "$1" | tr -d '\r' | awk -F'/' '/^rtt|^round-trip/ {print $5}'
}

iperf() { # target -> "mbps cpu_busy_percent cpu_softirq_percent"
  on 1 sh -c "head -1 /proc/stat > /tmp/s0; iperf3 -J -c $1 -t $IPERF_S > /tmp/iperf.json; head -1 /proc/stat > /tmp/s1"
  on 1 python3 -c "
import json
r = json.load(open('/tmp/iperf.json'))
s0, s1 = ([int(x) for x in open(f).read().split()[1:]] for f in ('/tmp/s0', '/tmp/s1'))
d = [b - a for a, b in zip(s0, s1)]
total = sum(d[:8])
print('%.1f %.1f %.1f' % (r['end']['sum_received']['bits_per_second'] / 1e6,
                          100 * (total - d[3] - d[4]) / total, 100 * d[6] / total))
"
}

summary() { # label values...
  on_server python3 -c "
import statistics as s, sys
v = [float(x) for x in sys.argv[2:]]
print('| %s | %.3f | %.3f | %.3f |' % (sys.argv[1], s.mean(v), min(v), max(v)))
" "$@"
}

declare -a rtt_lan rtt_ovl bw_lan bw_ovl cpu_lan cpu_ovl sirq_lan sirq_ovl
for i in $(seq 1 "$RUNS"); do
  rtt_lan+=("$(rtt "$LAN_B")")
  rtt_ovl+=("$(rtt "$OVL_B")")
  read -r bw cpu sirq <<<"$(iperf "$LAN_B" | tr -d '\r')"
  bw_lan+=("$bw"); cpu_lan+=("$cpu"); sirq_lan+=("$sirq")
  read -r bw cpu sirq <<<"$(iperf "$OVL_B" | tr -d '\r')"
  bw_ovl+=("$bw"); cpu_ovl+=("$cpu"); sirq_ovl+=("$sirq")
  echo "run $i: rtt lan=${rtt_lan[-1]} ovl=${rtt_ovl[-1]} ms | iperf lan=${bw_lan[-1]} ovl=${bw_ovl[-1]} Mbit/s | cpu busy lan=${cpu_lan[-1]} ovl=${cpu_ovl[-1]} % | softirq lan=${sirq_lan[-1]} ovl=${sirq_ovl[-1]} %"
done

echo
echo "| Metric | Mean | Min | Max |"
echo "|---|---|---|---|"
summary "RTT LAN (ms)" "${rtt_lan[@]}"
summary "RTT overlay (ms)" "${rtt_ovl[@]}"
summary "Throughput LAN (Mbit/s)" "${bw_lan[@]}"
summary "Throughput overlay (Mbit/s)" "${bw_ovl[@]}"
summary "System CPU busy during iperf3, LAN (%)" "${cpu_lan[@]}"
summary "System CPU busy during iperf3, overlay (%)" "${cpu_ovl[@]}"
summary "System CPU in softirq during iperf3, LAN (%)" "${sirq_lan[@]}"
summary "System CPU in softirq during iperf3, overlay (%)" "${sirq_ovl[@]}"
echo "CPU figures cover the whole host ($(on 1 nproc | tr -d '\r') CPUs), so they include kernel encryption"

echo
echo "client agent memory (VmRSS of python3 -m client):"
for n in $(seq 1 "$(clients)"); do
  on "$n" python3 -c "
import glob, os
for status in glob.glob('/proc/[0-9]*/status'):
    pid = status.split('/')[2]
    if pid == str(os.getpid()):
        continue
    try:
        cmd = open(f'/proc/{pid}/cmdline').read().replace(chr(0), ' ')
        if '-m client join' in cmd:
            print('client-$n', [l for l in open(status) if l.startswith('VmRSS')][0].strip())
    except OSError:
        pass
" | tr -d '\r'
done

echo
echo "join time of a new client (container start -> overlay ping both ways):"
declare -a join_out join_in
for i in $(seq 1 "$RUNS"); do
  n=$(( $(clients) + 1 ))
  t0=$(date +%s.%N)
  dc up -d --no-recreate --scale client="$n" client >/dev/null 2>&1
  until on "$n" test -f /var/lib/overlay-client/state.json 2>/dev/null; do sleep 0.2; done
  new_ip=$(overlay_ip "$n")
  until on "$n" ping -c 1 -W 1 "$OVL_A" >/dev/null 2>&1; do :; done
  t1=$(date +%s.%N)
  until on 1 ping -c 1 -W 1 "$new_ip" >/dev/null 2>&1; do :; done
  t2=$(date +%s.%N)
  join_out+=("$(on_server python3 -c "print(round($t1 - $t0, 2))" | tr -d '\r')")
  join_in+=("$(on_server python3 -c "print(round($t2 - $t0, 2))" | tr -d '\r')")
  echo "run $i: client-$n ($new_ip) new->existing ${join_out[-1]} s, existing->new ${join_in[-1]} s"
done
echo "| Metric | Mean | Min | Max |"
echo "|---|---|---|---|"
summary "Join: new client reaches existing (s)" "${join_out[@]}"
summary "Join: existing client reaches new (s)" "${join_in[@]}"
