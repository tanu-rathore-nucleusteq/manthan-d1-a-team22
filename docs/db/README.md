# Database setup

PostgreSQL 18 in Docker with every ReturnRight table, created from [schema_v2.sql](schema_v2.sql).

## Start it

From the repository root:

```
docker compose up -d db
```

The first start creates the tables, which takes about 10 seconds. `docker compose ps` shows the `db` service as `healthy` when it is ready.

## Connect

| Setting | Value |
|---|---|
| Host and port | `localhost:5434` from your laptop, `db:5432` from other containers |
| Database, user, password | `returnright`, `returnright`, `change-me` |
| Schema | `returnright` (the default search path, so no prefix is needed) |
| App connection string | `postgresql+psycopg://returnright:change-me@localhost:5434/returnright` |
| psql | `docker compose exec db psql -U returnright` |

If port 5434 is taken on your laptop, create a `.env` file in the repository root with `DB_PORT=5435` (any free port).

## Rebuild after a schema change

The tables are created only when the database is first created. After `schema_v2.sql` changes, rebuild it. This deletes all data in it:

```
docker compose down -v
docker compose up -d db
```

## Use an existing Postgres container instead

To create the tables in a container you already run (for example `pg` on port 5433), from the repository root:

```
docker cp docs/db/schema_v2.sql pg:/tmp/schema_v2.sql
docker exec pg psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f /tmp/schema_v2.sql
```

This drops and recreates the `returnright` schema in that database, so any data in it is lost.
