"""Lab manager: sessions, TTL/quotas/queue, deploy/destroy/snapshot/reset.

This is the orchestrator seam the driver interface was designed for. It
loads a lab's topology, resolves each node to a driver, renders startup
configs, deploys via the Containerlab runner (Docker fallback), waits for
the boot probes, and owns the session lifecycle.
"""

from __future__ import annotations

import logging
import secrets
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from netlab_drivers import get_driver
from netlab_shared.errors import (
    LabNotFoundError,
    QuotaExceededError,
    RunnerError,
)
from netlab_topology import LabDefinition, LabTopology, load_lab_definition, load_topology
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.metrics import deploy_total, lab_boot_seconds, labs_running
from app.db.models import LabSession, User
from app.labs.queue import DeployQueue
from app.labs.runner import ContainerlabRunner, DockerRunner, render_topology_file

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _utc_aware(value: datetime | None) -> datetime | None:
    """SQLite stores datetimes naive; normalise to aware UTC for compares."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class LabManager:
    def __init__(self, db: Session, queue: DeployQueue | None = None):
        self.db = db
        self.queue = queue or DeployQueue()

    # -- lab catalogue --------------------------------------------------

    def list_labs(self) -> list[LabDefinition]:
        labs: list[LabDefinition] = []
        labs_dir = Path(settings.labs_dir)
        if not labs_dir.exists():
            return labs
        for lab_file in sorted(labs_dir.glob("*/lab.yml")):
            try:
                labs.append(load_lab_definition(lab_file))
            except Exception as exc:  # a broken lab must not hide the rest
                logger.warning("skipping broken lab %s: %s", lab_file, exc)
        return labs

    def get_lab(self, slug: str) -> tuple[LabDefinition, LabTopology]:
        lab_file = Path(settings.labs_dir) / slug / "lab.yml"
        if not lab_file.exists():
            raise LabNotFoundError(f"lab {slug!r} does not exist")
        lab = load_lab_definition(lab_file)
        topology_file = lab_file.parent / lab.topology_file
        topology = load_topology(topology_file)
        return lab, topology

    # -- quotas ---------------------------------------------------------

    def running_count(self) -> int:
        return (
            self.db.query(LabSession)
            .filter(LabSession.status == "running")
            .count()
        )

    def _check_quotas(self, topology: LabTopology) -> None:
        if self.running_count() >= settings.max_labs_per_host:
            raise QuotaExceededError(
                f"host is full ({settings.max_labs_per_host} labs running)"
            )
        if topology.total_cpu() > settings.max_cpu_per_lab:
            raise QuotaExceededError(
                f"lab needs {topology.total_cpu()} vCPU, "
                f"limit is {settings.max_cpu_per_lab}"
            )
        if topology.total_memory_mb() > settings.max_mem_per_lab_mb:
            raise QuotaExceededError(
                f"lab needs {topology.total_memory_mb} MB, "
                f"limit is {settings.max_mem_per_lab_mb}"
            )

    # -- sessions -------------------------------------------------------

    def create_session(
        self, user: User, lab_slug: str, ttl_seconds: int | None = None
    ) -> LabSession:
        """Create (and deploy) a session, or queue it when the host is full.
        Returns the LabSession row; status is 'running', 'deploying', or
        'queued'."""
        lab, topology = self.get_lab(lab_slug)
        try:
            self._check_quotas(topology)
        except QuotaExceededError:
            session = LabSession(
                id=secrets.token_hex(16),
                user_id=user.id,
                lab_slug=lab_slug,
                clab_name=self._clab_name(user.id, lab_slug),
                status="queued",
                cpu_limit=topology.total_cpu(),
                memory_limit_mb=topology.total_memory_mb(),
            )
            self.db.add(session)
            self.db.commit()
            self.queue.enqueue(user.id, lab_slug)
            logger.info("lab %s queued for user %s", lab_slug, user.id)
            return session

        session = LabSession(
            id=secrets.token_hex(16),
            user_id=user.id,
            lab_slug=lab_slug,
            clab_name=self._clab_name(user.id, lab_slug),
            status="deploying",
            cpu_limit=topology.total_cpu(),
            memory_limit_mb=topology.total_memory_mb(),
            expires_at=_now()
            + timedelta(seconds=ttl_seconds or settings.lab_ttl_seconds),
            last_activity_at=_now(),
        )
        self.db.add(session)
        self.db.commit()
        try:
            self.deploy(session, topology)
        except Exception:
            session.status = "failed"
            self.db.commit()
            raise
        return session

    @staticmethod
    def _clab_name(user_id: int, lab_slug: str) -> str:
        short = secrets.token_hex(4)
        return f"netlab-{user_id}-{lab_slug}-{short}"

    def deploy(self, session: LabSession, topology: LabTopology | None = None) -> None:
        """Deploy the lab for an existing session row."""
        _, topology = self.get_lab(session.lab_slug) if topology is None else (None, topology)
        started = _now()
        workdir = Path(tempfile.mkdtemp(prefix=f"netlab-{session.clab_name}-"))
        try:
            topology_file = render_topology_file(topology, workdir)
            runner = ContainerlabRunner(session.clab_name, topology_file)
            try:
                runner.deploy()
            except RunnerError as exc:
                if "command not found" in str(exc):
                    logger.warning(
                        "containerlab binary missing; falling back to Docker"
                    )
                    docker_runner = DockerRunner(session.clab_name, topology)
                    docker_runner.deploy()
                    runner = docker_runner
                else:
                    raise
            # Wait for every node's boot probe via its driver.
            for node_name, topo_node in topology.nodes.items():
                driver = get_driver(topo_node.kind)
                node_spec = self._node_spec(topo_node, topology)
                if not driver.ready(runner, node_spec):
                    raise RunnerError(
                        f"node {node_name!r} did not become ready "
                        f"(probe: {driver.boot_probe.command!r})"
                    )
            session.status = "running"
            session.last_activity_at = _now()
            self.db.commit()
            labs_running.inc()
            lab_boot_seconds.labels(driver="mixed").observe(
                (_now() - started).total_seconds()
            )
            deploy_total.labels(outcome="success").inc()
            logger.info("lab %s deployed for session %s", session.lab_slug, session.id)
        except Exception:
            deploy_total.labels(outcome="failure").inc()
            raise
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def destroy(self, session: LabSession) -> None:
        _, topology = self.get_lab(session.lab_slug)
        workdir = Path(tempfile.mkdtemp(prefix=f"netlab-{session.clab_name}-"))
        try:
            topology_file = render_topology_file(topology, workdir)
            runner = ContainerlabRunner(session.clab_name, topology_file)
            try:
                runner.destroy()
            except RunnerError as exc:
                if "command not found" not in str(exc):
                    raise
                DockerRunner(session.clab_name, topology).destroy()
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        was_running = session.status == "running"
        session.status = "destroyed"
        self.db.commit()
        if was_running:
            labs_running.dec()

    def snapshot(self, session: LabSession) -> dict[str, str]:
        """Capture each node's running config through its driver."""
        _, topology = self.get_lab(session.lab_slug)
        workdir = Path(tempfile.mkdtemp(prefix=f"netlab-{session.clab_name}-"))
        try:
            topology_file = render_topology_file(topology, workdir)
            runner = ContainerlabRunner(session.clab_name, topology_file)
            configs: dict[str, str] = {}
            for node_name, topo_node in topology.nodes.items():
                driver = get_driver(topo_node.kind)
                configs[node_name] = driver.snapshot(
                    runner, self._node_spec(topo_node, topology)
                )
            return configs
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def reset(self, session: LabSession) -> None:
        self.destroy(session)
        session.status = "deploying"
        session.expires_at = _now() + timedelta(seconds=settings.lab_ttl_seconds)
        self.db.commit()
        _, topology = self.get_lab(session.lab_slug)
        self.deploy(session, topology)

    def get_session(self, session_id: str) -> LabSession:
        session = self.db.get(LabSession, session_id)
        if session is None:
            raise LabNotFoundError(f"session {session_id!r} does not exist")
        return session

    def touch(self, session: LabSession) -> None:
        session.last_activity_at = _now()
        self.db.commit()

    def reap_expired(self) -> int:
        """Destroy sessions past TTL or idle timeout. Returns the count."""
        now = _now()
        expired = (
            self.db.query(LabSession)
            .filter(LabSession.status.in_(("running", "deploying", "queued")))
            .all()
        )
        count = 0
        for session in expired:
            expires_at = _utc_aware(session.expires_at)
            last_activity = _utc_aware(session.last_activity_at)
            ttl_hit = expires_at is not None and expires_at <= now
            idle_hit = (
                last_activity is not None
                and (now - last_activity).total_seconds()
                > settings.lab_idle_timeout_seconds
            )
            if ttl_hit or idle_hit:
                try:
                    self.destroy(session)
                except Exception as exc:  # never let one bad session stop the reaper
                    logger.warning("reaper failed for %s: %s", session.id, exc)
                    session.status = "destroyed"
                    self.db.commit()
                count += 1
        if count:
            logger.info("reaper destroyed %d expired sessions", count)
        return count

    # -- helpers --------------------------------------------------------

    @staticmethod
    def _node_spec(topo_node, topology: LabTopology):
        from netlab_drivers.base import NodeSpec

        return NodeSpec(
            name=topo_node.name,
            driver=topo_node.kind,
            image=topo_node.image,
            kind=topo_node.kind,
            startup_config=topo_node.startup_config,
            env=topo_node.env,
            cpu_limit=topo_node.cpu_limit,
            memory_limit_mb=topo_node.memory_limit_mb,
        )
