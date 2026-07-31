"""Locust load scenarios for local performance testing."""

from __future__ import annotations

import os

from locust import HttpUser, between, task


class TutorApiUser(HttpUser):
    wait_time = between(0.5, 2.0)
    token: str | None = None

    def on_start(self):
        res = self.client.post("/auth/guest")
        if res.ok:
            self.token = res.json().get("access_token")

    @property
    def auth_headers(self) -> dict:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def questions(self):
        self.client.get("/questions?limit=20")

    @task(2)
    def chapters(self):
        self.client.get("/chapters")

    @task(2)
    def learning_today(self):
        self.client.get("/learning/today/me", headers=self.auth_headers)

    @task(1)
    def learning_progress(self):
        self.client.get("/learning/progress/me", headers=self.auth_headers)

    @task(1)
    def ready(self):
        self.client.get("/health/ready")


# Run: locust -f locust/locustfile.py --host http://127.0.0.1:8000
