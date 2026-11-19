# Two-Router OSPF with a VLAN-Aware Switch

**Time:** ~45 minutes · **Level:** CCNA / early network engineering

## Topology

```
h1 (VLAN 10) ── sw1 ── r1 ── 10.0.12.0/30 ── r2 ── sw1 ── h2 (VLAN 20)
                  │         │                       │
               VLAN 10   10.0.10.1/24          10.0.20.1/24
```

- `r1` / `r2` — FRR routers, OSPF area 0. Loopbacks 1.1.1.1/32 and 2.2.2.2/32.
- `sw1` — Alpine Linux bridge with VLAN filtering. VLAN 10 and VLAN 20 are isolated at L2.
- `h1` — 10.0.10.10/24, gateway 10.0.10.1 (r1).  
  `h2` — 10.0.20.10/24, gateway 10.0.20.1 (r2).

## 1. Deploy

Open this lab in the UI and click **Deploy**. Wait for all five nodes to report ready (the FRR boot probe runs `show version` until it answers).

## 2. Verify the OSPF adjacency

Open the `r1` terminal:

```
show ip ospf neighbor
```

You should see r2 (2.2.2.2) in state **FULL**. If it shows INIT or nothing at all, check the link first:

```
show ip ospf interface brief
show interface eth1
```

Then on `r2`:

```
show ip ospf neighbor
show ip route ospf
```

You should see `1.1.1.1/32` — r1's loopback, learned via OSPF.

## 3. Prove the VLANs are isolated at L2

On `h1` try to reach `h2` **without** going through the routers (this should fail):

```
ping -c 3 10.0.20.10
```

This must **fail**. h1 and h2 are in different VLANs and `sw1` does not forward between them at Layer 2.

Confirm why on `sw1`:

```
bridge vlan show
```

`eth3` (h1) is only in VLAN 10; `eth4` (h2) is only in VLAN 20. There is no shared L2 path.

> **Gotcha:** If this ping *succeeds*, your VLANs are not isolated. Fix the switch config before moving on.

## 4. Prove the routers carry inter-VLAN traffic

Now that L2 isolation is confirmed, the same ping should succeed **via routing**:

```
# on h1
ping -c 3 10.0.20.10
```

It works because the path is:

`h1 → r1 (gateway) → OSPF → r2 → h2`

If it still fails, trace it:

```
# on h1
traceroute 10.0.20.10

# on r1
show ip route
```

You should see `10.0.20.0/24` via OSPF on r1, and `10.0.10.0/24` via OSPF on r2.

## 5. Break it (optional)

In the `r1` terminal, shut the OSPF link and watch the adjacency drop:

```
configure terminal
interface eth1
shutdown
```

Then `show ip ospf neighbor` on r2 — the neighbor disappears. Bring it back with `no shutdown` and watch it return to FULL. This is the failure mode the grading check is built around.

## 6. Grade it

Click **Run checks** in the objectives panel. Four objectives, all checked against live state:

1. OSPF adjacency FULL on r1
2. r2 learns `1.1.1.1/32` via OSPF
3. VLAN 10/20 isolated on sw1 (config analysis)
4. r1 has an OSPF route to `10.0.20.0/24`
