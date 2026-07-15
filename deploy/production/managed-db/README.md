# Managed Database (Strategic Productionization)

Phase 9 moves the platform off the demo SQLite file (`agentic_commerce.db`) to a
**managed Postgres** database (Amazon RDS, Google Cloud SQL, Azure Database for
PostgreSQL, or an operator-managed Postgres in Kubernetes).

## Why

- SQLite is single-writer and not suitable for the multi-replica deployment that
  GitOps enables (see `../gitops`).
- A managed service provides automated backups, patching, failover, and
  connection pooling (e.g. PgBouncer / RDS Proxy) so the application does not
  have to manage durability.

## How the application supports it

`src/merchant/db/database.py` is now driver-aware:

- `postgres://` URLs are normalized to `postgresql://` (the SQLAlchemy dialect),
  so managed-provider connection strings work without manual edits.
- The SQLite-only `check_same_thread` connect argument is only applied for
  SQLite; for Postgres it is omitted so engine creation does not fail.
- `pool_pre_ping=True` and `pool_recycle=1800` keep long-lived pooled
  connections healthy across provider idle timeouts.

The PSP uses the same `DATABASE_URL` contract, so both services point at the
same managed instance.

## Connecting to a real managed database

Set a single environment variable on the `merchant` and `psp` services:

```bash
export DATABASE_URL="postgresql://<user>:<password>@<managed-host>:5432/agentic_commerce?sslmode=require"
```

Production guidance:

- **Never** commit the password. Inject `DATABASE_URL` from a secrets manager
  (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, or the Kubernetes
  `ExternalSecrets` operator). The GitOps base references `DATABASE_URL` as an
  opaque Secret (see `../gitops/base/secret.yaml`).
- Require TLS with `sslmode=require` (or `verify-full` with a CA bundle).
- Prefer a connection pooler (RDS Proxy / PgBouncer) in front of the managed
  instance so horizontal replicas do not exhaust connections.

## Provisioning schema

Run the idempotent migration step against the managed DB before rolling the
application:

```bash
python deploy/production/managed-db/db-migrate.py
```

This runs `SQLModel.metadata.create_all` plus the initial seed. It is safe to
re-run; existing rows are skipped.

## Local production-shaped validation

`docker-compose.managed-db.yml` provides a Postgres container wired exactly the
way the managed endpoint would be, so the full stack can be exercised with a
real client/server database before cutover:

```bash
docker network create acp-infra-network || true
docker compose \
  -f docker-compose.infra.yml \
  -f docker-compose.yml \
  -f deploy/production/managed-db/docker-compose.managed-db.yml \
  up -d
```
