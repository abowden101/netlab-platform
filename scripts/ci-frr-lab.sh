#!/usr/bin/env bash
# CI integration: deploy the 2-node FRR fixture, wait for the OSPF
# adjacency to reach FULL, then destroy the lab.
# Requires: docker, containerlab. Run from the repo root.
set -euo pipefail

FIXTURE="packages/drivers/tests/fixtures/two-node-frr.clab.yml"
LAB="ci-two-node-frr"

cleanup() {
  echo "--- destroying lab ---"
  containerlab destroy -t "$FIXTURE" --cleanup || true
}
trap cleanup EXIT

echo "--- deploying $LAB ---"
containerlab deploy -t "$FIXTURE"

echo "--- waiting for OSPF FULL on r1 ---"
deadline=$((SECONDS + 300))
while true; do
  if docker exec "clab-${LAB}-r1" vtysh -c "show ip ospf neighbor" 2>/dev/null \
      | grep -q "FULL"; then
    echo "OSPF adjacency is FULL"
    break
  fi
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "ERROR: OSPF did not reach FULL within 300s"
    docker exec "clab-${LAB}-r1" vtysh -c "show ip ospf neighbor" || true
    docker exec "clab-${LAB}-r1" vtysh -c "show ip ospf interface brief" || true
    exit 1
  fi
  sleep 5
done

echo "--- verifying r2 learned r1's loopback ---"
docker exec "clab-${LAB}-r2" vtysh -c "show ip route ospf" | grep -q "1.1.1.1/32"
echo "r2 has 1.1.1.1/32 via OSPF"
echo "INTEGRATION OK"
