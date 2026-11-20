"""Load test: customers look up demo orders while staff read the dashboard and the refund list.

Read-only: it never creates returns or pays refunds, so the demo data stays as seeded.
Install: pip install -r tests/load/requirements.txt
Run (stack up): locust -f tests/load/locustfile.py --host http://127.0.0.1:8000
Headless: add --headless -u 50 -r 5 -t 2m
"""

import random

from locust import HttpUser, between, task

DEMO_EMAIL = "asha.verma@example.com"
DEMO_ORDERS = [f"ORD-DEMO-{number:02d}" for number in range(1, 11)]
DEMO_PASSWORD = "change-me-demo"


class CustomerUser(HttpUser):
    """A customer checking which items of a demo order can be returned."""

    weight = 8
    wait_time = between(1, 3)

    @task
    def look_up_order(self) -> None:
        self.client.post(
            "/api/v1/orders/lookup",
            json={"order_number": random.choice(DEMO_ORDERS), "email": DEMO_EMAIL},
        )


class StaffUser(HttpUser):
    """Signs in once, then sends the bearer token with every request."""

    abstract = True
    username = ""
    wait_time = between(2, 5)

    def on_start(self) -> None:
        reply = self.client.post(
            "/api/v1/auth/login", json={"username": self.username, "password": DEMO_PASSWORD}
        )
        reply.raise_for_status()
        self.client.headers["Authorization"] = f"Bearer {reply.json()['access_token']}"


class ManagerUser(StaffUser):
    """Operations manager watching the dashboard."""

    weight = 1
    username = "manager1"

    @task
    def view_dashboard(self) -> None:
        self.client.get("/api/v1/dashboard")


class FinanceUser(StaffUser):
    """Finance reviewer reading refunds; the endpoint is for finance reviewers only."""

    weight = 1
    username = "finance1"

    @task
    def list_refunds(self) -> None:
        self.client.get("/api/v1/finance/refunds")
