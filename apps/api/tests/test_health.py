def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_metrics_exposes_netlab_metrics(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert b"netlab_labs_running" in resp.content
    assert b"netlab_deploys_total" in resp.content


def test_oauth_github_unconfigured_returns_503(client):
    # No OAuth credentials are configured in the test env.
    resp = client.get("/api/v1/auth/github", follow_redirects=False)
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"]
