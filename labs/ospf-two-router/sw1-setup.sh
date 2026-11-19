#!/bin/sh
# sw1 — VLAN-aware Linux bridge (alpine + iproute2).
#
# Ports:
#   eth1 -> r1 (VLAN 10, untagged)   eth2 -> r2 (VLAN 20, untagged)
#   eth3 -> h1 (VLAN 10, untagged)   eth4 -> h2 (VLAN 20, untagged)
# VLAN filtering is on, so a frame in VLAN 10 can never reach a VLAN 20
# port at L2. Inter-VLAN traffic must go through the routers (r1/r2).
set -e
apk add --no-cache iproute2 bridge-utils >/dev/null 2>&1 || true

ip link add name br0 type bridge vlan_filtering 1 || true
ip link set br0 up

for p in eth1 eth2 eth3 eth4; do
  ip link set "$p" master br0
  ip link set "$p" up
done

# Drop the default VLAN 1 membership, then assign PVIDs.
for p in eth1 eth2 eth3 eth4; do
  bridge vlan del dev "$p" vid 1 || true
done
bridge vlan add dev eth1 vid 10 pvid untagged
bridge vlan add dev eth2 vid 20 pvid untagged
bridge vlan add dev eth3 vid 10 pvid untagged
bridge vlan add dev eth4 vid 20 pvid untagged

echo "sw1 bridge ready:"
bridge vlan show
