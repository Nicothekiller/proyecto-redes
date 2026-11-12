#!/usr/bin/env bash
# Checks that every client reaches every other client over the overlay.
# Usage: bench/mesh.sh [limit-seconds]

source "$(dirname "$0")/lib.sh"

limit=${1:-25}
n=$(clients)
declare -A ip
for i in $(seq 1 "$n"); do ip[$i]=$(overlay_ip "$i"); done
echo "clients=$n overlay: ${ip[*]}"

failed=0
for i in $(seq 1 "$n"); do
  for j in $(seq 1 "$n"); do
    [ "$i" = "$j" ] && continue
    if tries=$(wait_ping "$i" "${ip[$j]}" "$limit"); then
      echo "client-$i -> client-$j (${ip[$j]}): ok after $tries s"
    else
      echo "client-$i -> client-$j (${ip[$j]}): FAILED"
      failed=1
    fi
  done
done
exit "$failed"
