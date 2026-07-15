# Phase 9: Strategic Productionization

This directory contains the productionization work for the Agentic Commerce
platform across three pillars:

| Pillar | Path | What it delivers |
| ------ | ---- | ---------------- |
| **GitOps** | [`gitops/`](./gitops) | Argo CD + Kustomize deployment topology (base + staging/production overlays) so cluster state is reconciled from git. |
| **Managed DB** | [`managed-db/`](./managed-db) | Driver-aware DB engine + a Postgres override + idempotent migration step, replacing the demo SQLite file. |
| **mTLS** | [`mtls/`](./mtls) | Mutual TLS for east-west traffic via a step-ca mesh, per-service certs, and an nginx client-cert-verification config. |

## How the three pillars fit together

1. **Managed DB** supplies durable state. The application reads `DATABASE_URL`
   and transparently supports a managed Postgres endpoint; the migration step
   (`managed-db/db-migrate.py`) provisions schema idempotently.
2. **GitOps** is the delivery mechanism. The Kustomize base deploys the
   services with `DATABASE_URL` and API keys injected as a Secret (via External
   Secrets in real environments), and scales per environment.
3. **mTLS** secures service-to-service traffic inside the cluster, enforcing
   that only members of the mesh (valid client cert) can call the backends.

## End-to-end (local, production-shaped)

```bash
docker network create acp-infra-network || true

# Managed DB + mTLS-shaped stack
docker compose \
  -f docker-compose.infra.yml \
  -f docker-compose.yml \
  -f deploy/production/managed-db/docker-compose.managed-db.yml \
  -f deploy/production/mtls/docker-compose.mtls.yml \
  up -d

# GitOps render (Argo CD would apply this against the cluster)
kubectl kustomize deploy/production/gitops/overlays/production
```

## Code changes

- `src/merchant/db/database.py`: `get_engine()` now normalizes `postgres://`
  to `postgresql://`, only applies the SQLite `check_same_thread` connect arg
  for SQLite, and sets `pool_pre_ping`/`pool_recycle` for managed-DB stability.
- `env.example`: documents `DATABASE_URL` (managed DB) and `TLS_ENABLED` /
  `CA_BUNDLE` (mTLS) knobs.

## Validation

`.github/workflows/gitops-validate.yml` runs on every change under
`deploy/production/**`: it syntax-checks the mTLS shell scripts, validates the
Compose overrides with `docker compose config`, renders the Kustomize overlays,
and dry-runs the resulting manifests with `kubectl`.
