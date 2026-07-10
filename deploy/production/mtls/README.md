# mTLS for East-West Traffic (Strategic Productionization)

Phase 9 hardens service-to-service communication with **mutual TLS (mTLS)**.
Every core service presents a certificate to its peers and verifies the
peer's certificate against the Agentic Commerce CA before exchanging traffic.

## Architecture

```
            +-------------------+
            |  step-ca (Smallstep)  <-- CA root (ca-bundle.crt)
            +-------------------+
                      |
            +-------------------+
            |  cert-provisioner |  issues per-service certs into `acp-certs`
            +-------------------+
       -----------------------------------------
       |                |              |        |
   merchant.acp     psp.acp      apps-sdk.acp   ui.acp
   (presents +     (presents +   (presents +   (presents +
    verifies)       verifies)      verifies)     verifies)
```

- Each service gets a cert whose SAN is its in-cluster DNS name
  (`merchant.acp.svc.cluster.local`, etc.) so the identity is tied to the
  service, not the pod IP.
- `nginx/mtls.conf` enforces `ssl_verify_client on;` so only mesh members
  (valid client cert) can reach the upstreams. `X-Client-Cert` is forwarded
  for audit.
- The CA root (`ca-bundle.crt`) is the trust anchor mounted into every service
  as `CA_BUNDLE`.

## Bootstrap

Requires the [`step` CLI](https://smallstep.com/docs/step-cli/).

```bash
# 1. Initialize the mesh CA (idempotent)
bash deploy/production/mtls/scripts/bootstrap-ca.sh

# 2. Issue per-service certificates
CA_URL=https://ca.acp.local:9000 \
  bash deploy/production/mtls/scripts/issue-certs.sh
```

Or, when running the full stack, the `cert-provisioner` container runs step 2
automatically once `step-ca` is healthy and writes certs into the `acp-certs`
volume.

## Run the mTLS-shaped stack

```bash
docker network create acp-infra-network || true
docker compose \
  -f docker-compose.infra.yml \
  -f docker-compose.yml \
  -f deploy/production/mtls/docker-compose.mtls.yml \
  up -d
```

Then point nginx at `nginx/mtls.conf` (replace the upstreams in `nginx.conf`)
so client-certificate verification is enforced at the edge of the mesh.

## Production notes

- The CA password and issued keys must live in a secrets manager / KMS, never
  in the repo. `secrets/ca` and `secrets/certs` are git-ignored locally.
- For a managed Kubernetes deployment, prefer a mesh that issues certs
  automatically (istio / linkerd / SPIRE) instead of the standalone step-ca
  shown here; the trust model (per-service SAN identities + CA bundle) is
  identical.
- Certificate rotation: re-run `issue-certs.sh` with a fresh `--not-after`, or
  wire step-ca renewals via the `step` auto-renew agent.
