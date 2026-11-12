#!/usr/bin/env bash
# Encrypted-traffic proof (issue #17): client-1 pings client-2 with a recognizable payload,
# once over the LAN and once over the overlay, while tcpdump listens on client-2's eth0.
# The LAN ping shows ICMP with the payload in clear; the overlay ping shows only WireGuard UDP.
# The pcaps are copied to bench/captures/ for Wireshark.
# Usage: bench/capture.sh   (needs the bench up with at least 2 clients)

source "$(dirname "$0")/lib.sh"

PAYLOAD_HEX=6f7665726c61792d70726f6f66
PAYLOAD_TEXT=overlay-proof
LAN_A=$(lan_ip 1)
LAN_B=$(lan_ip 2)
OVL_B=$(overlay_ip 2)
mkdir -p captures
wait_ping 1 "$OVL_B" 25 >/dev/null

capture() { # name target
  on 2 sh -c "rm -f /tmp/$1.pcap; (tcpdump -i eth0 -U -w /tmp/$1.pcap 'host $LAN_A and (icmp or udp)' >/dev/null 2>&1 &) ; sleep 1"
  on 1 ping -c 5 -i 0.2 -p "$PAYLOAD_HEX" "$2" >/dev/null
  sleep 1
  on 2 sh -c 'kill $(cat /proc/[0-9]*/stat 2>/dev/null | grep "(tcpdump)" | cut -d" " -f1) 2>/dev/null; sleep 1'
  docker cp "overlay-bench-client-2:/tmp/$1.pcap" "captures/$1.pcap" >/dev/null
}

report() { # name
  local packets icmp udp payload
  packets=$(on 2 tcpdump -nn -r "/tmp/$1.pcap" 2>/dev/null | tr -d '\r')
  icmp=$(grep -c "ICMP echo" <<<"$packets" || true)
  udp=$(grep -c "UDP" <<<"$packets" || true)
  payload=$(on 2 tcpdump -nn -A -r "/tmp/$1.pcap" 2>/dev/null | grep -c "$PAYLOAD_TEXT" || true)
  echo "== $1: $icmp ICMP echo packets, $udp UDP packets, payload '$PAYLOAD_TEXT' visible in $payload packets"
  head -4 <<<"$packets"
  on 2 tcpdump -nn -A -r "/tmp/$1.pcap" 2>/dev/null | tr -d '\r' | grep -m 1 -o ".\{0,20\}$PAYLOAD_TEXT.\{0,10\}" || echo "  (payload not found in any packet)"
}

capture lan "$LAN_B"
capture overlay "$OVL_B"
report lan
report overlay
echo "pcaps: bench/captures/lan.pcap bench/captures/overlay.pcap"
