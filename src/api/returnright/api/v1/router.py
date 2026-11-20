"""Mounts every endpoint router under /api/v1."""

from fastapi import APIRouter

from returnright.api.v1.endpoints import (
    audit,
    auth,
    dashboard,
    finance,
    health,
    orders,
    returns,
    warehouse,
)
from returnright.core.constants import API_V1_PREFIX

api_router = APIRouter(prefix=API_V1_PREFIX)

for module in (health, auth, orders, returns, warehouse, finance, dashboard, audit):
    api_router.include_router(module.router)
