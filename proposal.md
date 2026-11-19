# Network Lab Platform — Proposal: Repo Layout + Driver Interface

**Date:** 2026-11-19
**Status:** AWAITING Tonio's approval — nothing beyond this proposal is built yet.
**Direction (confirmed by Tonio):** Real emulation backend (Containerlab; GNS3/CML-class), NOT a CLI simulator. Repo structured for GitHub with CI, docs, and a deployable demo.

## Decisions made in this proposal

1. **Backend: Python + FastAPI.** The grading stack is Python (pyATS/Genie), so the backend speaks the same language as the checks. FastAPI also generates the OpenAPI spec the spec requires, for free.
2. **Orchestrator: Containerlab.** Topologies are Containerlab YAML, stored in the repo. Docker Compose is the fallback for hosts without Containerlab (generated from the same topology).
3. **Console: xterm.js ↔ WebSocket ↔ backend proxy ↔ node console.** Per driver: SSH where the NOS supports it, `docker exec` serial-style where it doesn't. Reconnect, session logging, read-only observer mode for instructors.
4. **Sessions:** one isolated Containerlab lab per user session, namespace `netlab-<user>-<lab>-<id>`, default TTL 2h, idle-timeout auto-destroy 30 min, CPU/RAM quotas per lab, queue when the host is full.
5. **Images:** FRR + Linux hosts are public/free — CI runs the 2-node FRR lab. cEOS, vJunos, IOS-XE are BYO/licensed, never bundled. Upload flow with SHA256 checksum + license notice.
6. **Demo path:** Docker Compose local dev. A hosted demo needs a real host (VPS or his laptop) — GitHub Pages cannot run containers, so the "deployable demo" is a Compose/Helm deployment, not a static site.
7. **Auth:** GitHub OAuth first, Google second. Roles: instructor / student.

## Repo layout

```
netlab-platform/
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── docker-compose.yml              # local dev: api + web + postgres + redis
├── .github/
│   └── workflows/
│       ├── ci.yml                  # lint, typecheck, test, build
│       ├── topology-validate.yml   # validate labs/**/*.yml on every PR
│       └── publish.yml             # container image publish
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/               # config, security, logging, metrics
│   │   │   ├── auth/               # OAuth GitHub/Google, roles
│   │   │   ├── labs/               # sessions, TTL, quotas, queue
│   │   │   ├── console/            # WebSocket proxy to node consoles
│   │   │   ├── grading/            # pyATS/Batfish check runners
│   │   │   └── db/                 # SQLAlchemy models, Alembic migrations
│   │   ├── tests/
│   │   └── Dockerfile
│   └── web/                        # React + TS + Vite
│       ├── src/
│       │   ├── components/         # TopologyCanvas, TerminalPane, FileBrowser, ObjectivesPanel
│       │   ├── pages/              # Labs, LabSession, InstructorDashboard
│       │   ├── api/                # generated OpenAPI client
│       │   └── lib/
│       ├── tests/                  # Playwright E2E
│       └── Dockerfile
├── packages/
│   ├── drivers/                    # NOS driver interface + implementations (Python)
│   │   ├── netlab_drivers/
│   │   │   ├── base.py             # NodeDriver ABC (below)
│   │   │   ├── frr.py
│   │   │   ├── vyos.py
│   │   │   ├── ceos.py
│   │   │   ├── vjunos.py
│   │   │   └── iosxe.py            # BYO image only
│   │   └── tests/                  # unit tests per driver
│   ├── topology/                   # Containerlab YAML load / validate / generate
│   └── shared/                     # shared types, errors
├── labs/                           # coursework
│   └── ospf-two-router/            # sample lab (deliverable 4)
│       ├── topology.clab.yml
│       ├── lab.yml                 # objectives + grading checks
│       └── guide.md
├── infra/
│   ├── helm/                       # hosted deployment chart
│   └── terraform/                  # hosted deployment (VPS/cloud)
├── docs/
│   ├── architecture.md
│   ├── byo-image-guide.md          # Cisco IOS-XE BYO image + license notice
│   ├── instructor-guide.md
│   └── api.md                      # generated OpenAPI
└── scripts/
    └── dev-setup.sh
```

## Driver interface (Python — `packages/drivers/netlab_drivers/base.py`)

Every NOS is a driver. The orchestrator only ever talks to this interface; adding a
vendor means adding one file + one registry line, nothing else changes.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

class ConsoleMethod(str, Enum):
    SSH = "ssh"        # console over SSH (cEOS, vJunos, VyOS)
    SERIAL = "serial"  # console via `docker exec` (IOS-XE, FRR)
    TELNET = "telnet"  # legacy fallback

@dataclass(frozen=True)
class Credentials:
    username: str
    password: str
    enable_password: str | None = None   # IOS enable secret

@dataclass(frozen=True)
class BootProbe:
    """How the backend knows a node is ready for a console."""
    kind: str          # "ssh" | "exec" | "tcp"
    command: str       # e.g. "show version"; "" for a bare TCP connect
    expect: str        # substring that must appear in output
    timeout_s: int = 300
    interval_s: int = 5

@dataclass
class NodeSpec:
    name: str
    driver: str              # registry key, e.g. "frr"
    image: str               # resolved container image ref
    kind: str                # containerlab node kind
    startup_config: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    cpu_limit: float = 1.0
    memory_limit_mb: int = 512
```

```python
class NodeDriver(ABC):
    """One driver per NOS. All five spec'd attributes live here."""
    name: str                                  # "frr" | "vyos" | "ceos" | "vjunos" | "ios-xe" | "linux"
    kind: str                                  # containerlab kind, e.g. "linux", "ceos"
    default_image: str                         # e.g. "frrouting/frr:v10.4.1"
    default_credentials: Credentials
    console_method: ConsoleMethod
    boot_probe: BootProbe

    @abstractmethod
    def startup_config(self, node: NodeSpec) -> str:
        """Render the node's startup config from template + node vars."""

    @abstractmethod
    def ready(self, runner: "ContainerlabRunner", node: NodeSpec) -> bool:
        """Run the boot probe; True when the node accepts a console."""

    # Defaults — override only when the NOS needs it:
    def exec(self, runner, node: NodeSpec, command: str) -> str: ...
    def console_command(self, node: NodeSpec) -> list[str]: ...
    def snapshot(self, runner, node: NodeSpec) -> str: ...
```

Registry + orchestrator seam:

```python
DRIVERS: dict[str, type[NodeDriver]] = {}   # populated by entry points

def get_driver(name: str) -> NodeDriver: ...

class LabSession:                            # orchestrator (apps/api/app/labs)
    def deploy(self, topology) -> Lab: ...
    def destroy(self, lab_id: str) -> None: ...
    def snapshot(self, lab_id: str) -> str: ...
    def reset(self, lab_id: str) -> None: ...
    def console_stream(self, lab_id: str, node: str): ...  # WebSocket
```

## Grading check shape (`labs/<name>/lab.yml`)

```yaml
objectives:
  - id: ospf-adjacency
    title: "OSPF adjacency FULL on R1 Gi0/0"
    check:
      engine: pyats            # or batfish (config analysis, no live traffic needed)
      node: R1
      command: show ip ospf neighbor
      expect:
        state: FULL
        interface: GigabitEthernet0/0
```

## Deliverable order (per spec)

1. README with architecture diagram, quick start, BYO-image guide.
2. Backend skeleton + driver interface + FRR driver end to end.
3. Frontend: topology canvas + one live terminal per node.
4. Sample lab: two-router OSPF + VLAN-aware switch + grading check.
5. CI pipeline + test suite.
6. Second driver (cEOS or VyOS) to prove the abstraction.
7. Cisco IOS-XE driver via the BYO image flow.

## Open questions for Tonio

- Repo name: `netlab-platform` ok, or `subnet-lab` (his subnetTonio brand)?
- Demo host: his laptop, or a VPS? (Decides when the hosted deployment lands.)
- Sample lab: spec says two-router OSPF + VLAN-aware switch — confirm, or use his
  4-router OSPF/BGP lab (R1/R2 OSPF, R3/R4 eBGP) instead?
