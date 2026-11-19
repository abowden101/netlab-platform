# Instructor Guide

## Roles

| Role | Can |
|---|---|
| `student` | Deploy labs, use consoles, run grading checks, view own progress |
| `instructor` | Everything a student can, plus: view all students' progress, join any console in read-only observer mode, reset/snapshot any session, create and edit labs |
| `admin` | Everything, plus: manage users, images, and host quotas |

Roles are assigned in the database (or via the admin API). OAuth sign-in
defaults new users to `student`.

## Creating a lab

A lab is a directory under `labs/<slug>/` with three files:

```
labs/my-lab/
├── topology.clab.yml   # Containerlab topology (nodes, kinds, images, links)
├── lab.yml             # objectives + automated checks
└── guide.md            # step-by-step student guide
```

Run `python scripts/validate-topologies.py` before committing — CI enforces
it on every PR touching `labs/`. See `labs/README.md` for the full schema.

## The instructor dashboard

Open **Instructor** in the UI to see, per lab:

- Which students have deployed, and whether their sessions are running,
  expired, or queued
- Per-objective pass/fail for every student, with the evidence the check
  captured (command output excerpt for pyATS, config excerpt for Batfish)
- Aggregate pass rates per objective — the fastest way to spot a lab step
  that is unclear or a check that is too strict

## Observing a student console

From the dashboard, open any running session and click **Observe**. You join
the student's console in read-only mode: you see their keystrokes and output
live, but your input is dropped server-side. The session transcript is also
saved on the host for later review.

## Reset and snapshot

- **Reset** destroys the student's lab and re-deploys it from the declared
  topology. Use it when a student has broken the lab beyond repair.
- **Snapshot** captures each node's running config through its driver and
  stores it on the session. Students can download their snapshot to compare
  against the intended config.

## Grading

Checks are declared in `lab.yml`:

```yaml
objectives:
  - id: ospf-adjacency
    title: "OSPF adjacency FULL on R1 Gi0/0"
    check:
      engine: pyats
      node: r1
      command: show ip ospf neighbor
      expect:
        state: FULL
```

- `pyats` runs the command on the live node and matches `expect` against
  the output (substring or regex). If Genie is installed it parses the
  output first and matches against the parsed structure.
- `batfish` analyses the node's startup-config offline (e.g. ACL coverage).
  It never sends traffic.

Results are stored per student and are immutable once recorded — re-running
checks appends a new attempt rather than overwriting.

## Quotas and the queue

Default limits (configurable in `.env`): 8 concurrent labs per host,
4 vCPU / 4096 MB per lab, 2-hour TTL, 30-minute idle timeout. When the host
is full, deploy requests queue FIFO and the student sees their position.
Raise `MAX_LABS_PER_HOST` only if the host has the headroom — each FRR node
is small, but IOS-XE and vJunos nodes are not.
