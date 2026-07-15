# GitOps Deployment (Strategic Productionization)

Phase 9 deploys the platform via **GitOps** using [Argo CD](https://argoproj.github.io/cd/)
and [Kustomize](https://kustomize.io/). The cluster state lives entirely in
this repository; Argo CD continuously reconciles the live cluster to the
manifests under `deploy/production/gitops`.

## Layout

```
deploy/production/gitops/
├── base/                      # Environment-agnostic manifests (Deployments, Services, Ingress)
│   ├── namespace.yaml
│   ├── configmap.yaml         # Non-secret service config (in-cluster DNS URLs)
│   ├── secret.yaml            # Placeholder; use External Secrets in prod (see file header)
│   ├── merchant.yaml
│   ├── psp.yaml
│   ├── apps-sdk.yaml
│   ├── ui.yaml
│   ├── ingress.yaml           # nginx ingress, TLS redirect
│   └── kustomization.yaml
├── overlays/
│   ├── staging/               # 1 replica each, image tag `staging`
│   └── production/            # 3 replicas, image tag `production`
└── argocd/
    ├── application-staging.yaml
    └── application-production.yaml
```

## How it works

1. CI builds and pushes images tagged by environment (`staging`, `production`,
   or a commit SHA) to `ghcr.io/...`.
2. The image tag is updated in the overlay `kustomization.yaml` (or via
   `kustomize edit set image` in CI).
3. Argo CD watches `main`, renders the overlay with Kustomize, and applies it
   with `prune` + `selfHeal` so drift is auto-corrected.

## Render and verify locally

```bash
# Render the staging overlay (requires kustomize or kubectl)
kubectl kustomize deploy/production/gitops/overlays/staging
kubectl kustomize deploy/production/gitops/overlays/production
```

## Register the Applications

```bash
kubectl apply -f deploy/production/gitops/argocd/application-staging.yaml
kubectl apply -f deploy/production/gitops/argocd/application-production.yaml
```

## Secrets

`base/secret.yaml` is a placeholder. In real environments, replace it with an
`ExternalSecret` (AWS/GCP/Azure Secret Manager or Vault) so `DATABASE_URL`,
`MERCHANT_API_KEY`, `PSP_API_KEY`, `WEBHOOK_SECRET`, and `NVIDIA_API_KEY` are
never stored in git. See the header comment in `base/secret.yaml`.

## Notes

- The GitOps base provides the deployment topology; the managed-database
  connection is supplied via `DATABASE_URL` (see `../managed-db`), and
  service-to-service encryption is covered by `../mtls`.
- The ingress terminates TLS; east-west traffic hardening is described in
  `../mtls` (mTLS via a service mesh or per-pod certificates).
