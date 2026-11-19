"""Grading engine: run a lab's objective checks and store the results."""

from __future__ import annotations

import logging

from netlab_topology import LabDefinition
from sqlalchemy.orm import Session

from app.core.metrics import grade_checks_total
from app.db.models import Grade, LabProgress, LabSession
from app.grading.batfish_runner import run_batfish_check
from app.grading.checks import CheckResult
from app.grading.pyats_runner import run_pyats_check
from app.labs.manager import LabManager
from app.labs.runner import ContainerlabRunner

logger = logging.getLogger(__name__)


def run_checks(
    db: Session,
    manager: LabManager,
    session: LabSession,
    lab: LabDefinition,
    runner: ContainerlabRunner,
) -> list[CheckResult]:
    """Run every objective check for a session and persist results."""
    _, topology = manager.get_lab(session.lab_slug)
    results: list[CheckResult] = []
    for objective in lab.objectives:
        check = objective.check
        try:
            if check.engine == "pyats":
                topo_node = topology.nodes[check.node]
                node_spec = manager._node_spec(topo_node, topology)
                result = run_pyats_check(
                    runner,
                    check.node,
                    check.command,
                    check.expect,
                    node_spec=node_spec,
                    objective_id=objective.id,
                )
            elif check.engine == "batfish":
                result = run_batfish_check(
                    lab,
                    check.node,
                    check.expect,
                    config_file=check.config,
                    objective_id=objective.id,
                )
            else:
                result = CheckResult(
                    objective.id, False, f"unknown engine {check.engine!r}", check.engine
                )
        except Exception as exc:
            result = CheckResult(
                objective.id, False, f"check error: {exc}", check.engine
            )
        results.append(result)
        grade_checks_total.labels(result="pass" if result.passed else "fail").inc()
        db.add(
            LabProgress(
                user_id=session.user_id,
                lab_slug=session.lab_slug,
                objective_id=objective.id,
                status="passed" if result.passed else "failed",
                detail=result.evidence[:2000],
            )
        )
    passed = sum(1 for r in results if r.passed)
    db.add(
        Grade(
            user_id=session.user_id,
            lab_slug=session.lab_slug,
            session_id=session.id,
            score=passed,
            total=len(results),
        )
    )
    db.commit()
    logger.info(
        "graded session %s: %d/%d objectives passed",
        session.id,
        passed,
        len(results),
    )
    return results
