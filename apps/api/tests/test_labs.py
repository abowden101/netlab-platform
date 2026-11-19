"""Lab catalogue + deploy error-path tests.

The deploy test asserts the honest failure mode on a host without
Containerlab or Docker: the API returns 503 with a clear error instead of
pretending the lab deployed.
"""

import pytest


def test_list_labs_finds_sample_lab(client):
    resp = client.get("/api/v1/labs")
    assert resp.status_code == 200
    slugs = {lab["id"] for lab in resp.json()}
    assert "ospf-two-router" in slugs


def test_get_lab_detail_includes_guide(client):
    resp = client.get("/api/v1/labs/ospf-two-router")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"].startswith("Two-Router OSPF")
    assert len(body["objectives"]) == 4
    assert "OSPF" in body["guide"]


def test_get_unknown_lab_404(client):
    resp = client.get("/api/v1/labs/no-such-lab")
    assert resp.status_code == 404


def test_deploy_requires_auth(client):
    resp = client.post("/api/v1/labs", json={"lab_slug": "ospf-two-router"})
    assert resp.status_code == 401


def test_deploy_without_containerlab_or_docker_returns_503(student_headers, client):
    resp = client.post(
        "/api/v1/labs", json={"lab_slug": "ospf-two-router"}, headers=student_headers
    )
    # This VM has neither `containerlab` nor `docker`; the deploy fails
    # cleanly and the API says so instead of hanging.
    assert resp.status_code == 503
    assert "command not found" in resp.json()["detail"]


def test_deploy_unknown_lab_404(student_headers, client):
    resp = client.post(
        "/api/v1/labs", json={"lab_slug": "no-such-lab"}, headers=student_headers
    )
    assert resp.status_code == 404


@pytest.mark.skip(reason="needs a running session; covered by console-info test")
def test_placeholder():
    pass
