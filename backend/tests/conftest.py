"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Force mock model and local retrieval before app import
os.environ["TESTING"] = "1"
os.environ.setdefault("OPENROUTER_API_KEY", "")
os.environ.setdefault("MODEL_PROVIDER", "mock")
os.environ.setdefault("USE_LOCAL_RETRIEVAL", "true")

from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    res = client.post("/auth/guest")
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
