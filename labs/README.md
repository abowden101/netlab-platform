# Labs (coursework)

Every lab is a directory under `labs/<slug>/` with three files:

```
labs/<slug>/
├── topology.clab.yml   # Containerlab topology: nodes, kinds, images, links
├── lab.yml             # Objectives + automated grading checks
└── guide.md            # Step-by-step student guide
```

Optional extras in the same directory: startup configs (`*.frr.conf`,
`*.cfg`), setup scripts (`*-setup.sh`) — referenced from the topology.

## lab.yml schema

```yaml
id: my-lab                 # unique slug, matches the directory name
title: My Lab
description: What the student builds and proves.
topology: topology.clab.yml
estimated_minutes: 45
objectives:
  - id: unique-id
    title: Short human-readable goal
    description: What "done" looks like.
    check:
      engine: pyats        # or batfish
      node: r1             # node in the topology
      command: show ip ospf neighbor   # pyats only
      config: sw1-setup.sh             # batfish only: file to analyse
      expect:
        state: FULL        # pyats: value must appear in command output
        contains: "1.1.1.1/32"   # pyats: substring that must appear
        vlans: [10, 20]    # batfish: VLANs that must exist
        isolated: true     # batfish: no port in both VLANs
```

## Validation

```bash
python scripts/validate-topologies.py
```

CI runs this on every PR touching `labs/`. It checks YAML validity, node
kinds, image rules (public drivers must use public images), link endpoints,
and that every objective references a real node with a well-formed check.

## Current labs

| Lab | What it teaches |
|---|---|
| `ospf-two-router` | OSPF area 0 adjacency, loopback advertisement, VLAN isolation at L2, inter-VLAN routing via OSPF |
