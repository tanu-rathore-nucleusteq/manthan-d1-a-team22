#!/usr/bin/env bash
# Builds the ReturnRight images (API, mock payment gateway, web app), starts them with
# PostgreSQL and loads the synthetic demo data, then prints what was loaded and where to go.
#
#   scripts/start.sh            build, start, seed only if the database is empty
#   scripts/start.sh --reset    same, then wipe and reload fresh demo data
#   scripts/start.sh --stop     stop everything (data is kept)
#
# Windows PowerShell: scripts\start.ps1 [-Reset] [-Stop]
set -euo pipefail
cd "$(dirname "$0")/.."

case "${1:-}" in
  "" | --reset | --stop) ;;
  *) echo "Usage: scripts/start.sh [--reset | --stop]"; exit 2 ;;
esac

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Install Docker Desktop and try again."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop and try again."
  exit 1
fi

if [ "${1:-}" = "--stop" ]; then
  docker compose stop
  echo "Stopped. Run scripts/start.sh to start again; your data is kept."
  exit 0
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example (dummy values; change ports there if one is taken)."
fi

echo "==> Building images: returnright-api, returnright-gateway, returnright-web"
docker compose build

echo "==> Starting the database, gateway, API and web app (the API seeds an empty database)"
docker compose up -d --wait --wait-timeout 300

if [ "${1:-}" = "--reset" ]; then
  echo "==> Reloading fresh demo data"
  docker compose exec -T api python -m scripts.seed
fi

echo "==> Rows in the database"
docker compose exec -T db psql -U returnright -d returnright -tA -F $'\t' -c "
  SELECT 'products', count(*) FROM products
  UNION ALL SELECT 'customers', count(*) FROM customers
  UNION ALL SELECT 'orders', count(*) FROM orders
  UNION ALL SELECT 'returns', count(*) FROM returns
  UNION ALL SELECT 'refunds', count(*) FROM refunds
  UNION ALL SELECT 'ledger entries', count(*) FROM ledger_entries
  UNION ALL SELECT 'audit rows', count(*) FROM audit_log
  UNION ALL SELECT 'staff users', count(*) FROM staff_users"

# Read single values from .env (it may have Windows line endings, so it is not sourced).
env_value() {
  local value
  value=$(grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)
  echo "${value:-$2}"
}
cat <<EOF

ReturnRight is running.
  Web app    http://localhost:$(env_value WEB_PORT 8080)
  API docs   http://localhost:$(env_value API_PORT 8000)/docs
  Gateway    http://localhost:$(env_value GATEWAY_PORT 8001)/health
  Database   localhost:$(env_value DB_PORT 5434) (user and database: returnright)

  Staff sign-in: warehouse1, finance1, manager1 / $(env_value DEMO_PASSWORD change-me-demo)
  Customer: asha.verma@example.com with orders ORD-DEMO-01 to ORD-DEMO-10
            rohan.mehta@example.com with ORD-DEMO-11 (the 4th return flags the customer)

  Logs: docker compose logs -f api    Stop: scripts/start.sh --stop
EOF
