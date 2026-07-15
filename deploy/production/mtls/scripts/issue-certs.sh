#!/usr/bin/env bash
#
# Issue per-service mTLS certificates from the Agentic Commerce CA.
#
# Each core service receives a certificate whose SAN DNS name matches the
# in-cluster service DNS used for east-west traffic, e.g.
#   merchant -> merchant.acp.svc.cluster.local
#
# The issued cert/key are written to a shared volume mounted by the services,
# and the CA root is provided as the trust bundle (CA_BUNDLE).
#
# Requires the `step` CLI. Run after bootstrap-ca.sh (or inside the
# `cert-provisioner` container).
set -euo pipefail

CA_DIR="${CA_DIR:-$(dirname "$0")/../secrets/ca}"
OUT_DIR="${CERT_OUT_DIR:-$(dirname "$0")/../secrets/certs}"
ROOT_CERT="${CA_DIR}/certs/root_ca.crt"
PW_FILE="${CA_DIR}/ca.password"
CA_URL="${CA_URL:-https://ca.acp.local:9000}"
CA_PORT="${CA_PORT:-9000}"

mkdir -p "${OUT_DIR}"

if [[ ! -f "${ROOT_CERT}" ]]; then
  echo "[issue-certs] ERROR: CA root not found at ${ROOT_CERT}. Run bootstrap-ca.sh first." >&2
  exit 1
fi
if [[ ! -f "${PW_FILE}" ]]; then
  echo "[issue-certs] ERROR: CA password missing at ${PW_FILE}." >&2
  exit 1
fi
if ! command -v step >/dev/null 2>&1; then
  echo "[issue-certs] ERROR: 'step' CLI not found." >&2
  exit 1
fi

# service-name -> SAN DNS (matches Compose service DNS and K8s in-cluster DNS)
SERVICES=(
  "merchant:merchant.acp.svc.cluster.local"
  "psp:psp.acp.svc.cluster.local"
  "apps-sdk:apps-sdk.acp.svc.cluster.local"
  "ui:ui.acp.svc.cluster.local"
  "nginxc:nginx.acp.svc.cluster.local"
)

for entry in "${SERVICES[@]}"; do
  svc="${entry%%:*}"
  san="${entry##*:}"
  crt="${OUT_DIR}/${svc}.crt"
  key="${OUT_DIR}/${svc}.key"
  echo "[issue-certs] issuing cert for ${svc} (SAN ${san})"
  step ca certificate "${san}" "${crt}" "${key}" \
    --ca-url "${CA_URL}" \
    --root "${ROOT_CERT}" \
    --not-after 2160h \
    --provisioner-password-file "${PW_FILE}" \
    --san "${san}" \
    --san "localhost"
  chmod 600 "${key}"
done

# Publish the trust bundle for clients (CA_BUNDLE).
cp "${ROOT_CERT}" "${OUT_DIR}/ca-bundle.crt"
echo "[issue-certs] issued certs + ca-bundle.crt into ${OUT_DIR}"
