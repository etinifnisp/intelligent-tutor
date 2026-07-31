"""API integration tests — auth, learning, questions."""

from __future__ import annotations


def test_health_live(client):
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "alive"


def test_health_ready(client):
    res = client.get("/health/ready")
    assert res.status_code in (200, 503)
    body = res.json()
    assert "checks" in body


def test_health_metrics(client):
    res = client.get("/health/metrics")
    assert res.status_code == 200
    body = res.json()
    assert "latency" in body
    assert "corpus_count" in body


def test_guest_auth_flow(client):
    res = client.post("/auth/guest")
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] in {"GUEST", "STUDENT"}


def test_protected_route_requires_auth(client):
    res = client.get("/learning/summary/me")
    assert res.status_code == 401


def test_learning_summary_authenticated(client, auth_headers):
    res = client.get("/learning/summary/me", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "user_id" in body
    assert "narrative" in body


def test_learning_today_plan(client, auth_headers):
    res = client.get("/learning/today/me", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["session_minutes"] >= 1
    assert "weak_concepts" in body


def test_learning_progress(client, auth_headers):
    res = client.get("/learning/progress/me", headers=auth_headers)
    assert res.status_code == 200
    assert "total_attempts" in res.json()


def test_questions_endpoint(client):
    res = client.get("/questions?limit=5")
    assert res.status_code == 200
    body = res.json()
    assert body["total_matches"] >= 0
    assert isinstance(body["questions"], list)


def test_chapters_endpoint(client):
    res = client.get("/chapters")
    assert res.status_code == 200
    body = res.json()
    assert "Physics" in body


def test_latency_header(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert "X-Response-Time-Ms" in res.headers
