#!/usr/bin/env bash
#
# Bootstrap the Agentic Commerce service-mesh CA (Smallstep step-ca).
#
# Idempotent: if the CA already exists it is left untouched. Run once (or
# inside the `step-ca` container init) before issuing service certificates.
#
# Requires the `step` CLI (https://smallstep.com/docs/step-cli/).
set -euo pipefail

CA_NAME="${CA_NAME:-acp-mesh}"
PROVISIONER="${PROVISIONER_NAME:-acp-provisioner}"
CA_DIR="${CA_DIR:-$(dirname "$0")/../secrets/ca}"
PW_FILE="${CA_DIR}/ca.password"
CA_PORT="${CA_PORT:-9000}"

mkdir -p "${CA_DIR}"

if [[ -f "${CA_DIR}/config/ca.json" ]]; then
  echo "[bootstrap-ca] CA already initialized at ${CA_DIR}; skipping"
  exit 0
fi

if ! command -v step >/dev/null 2>&1; then
  echo "[bootstrap-ca] ERROR: 'step' CLI not found. Install step-cli first." >&2
  exit 1
fi

# A persistent password is required for non-interactive CA init. In production
# this should come from a secret manager, not a file in the repo.
if [[ ! -f "${PW_FILE}" ]]; then
  echo "[bootstrap-ca] generating CA password"
  openssl rand -base64 24 > "${PW_FILE}"
  chmod 600 "${PW_FILE}"
fi

echo "[bootstrap-ca] initializing CA '${CA_NAME}' on port ${CA_PORT}"
step ca init \
  --name "${CA_NAME}" \
  --dns "ca.acp.local,localhost" \
  --provisioner "${PROVISIONER}" \
  --password-file "${PW_FILE}" \
  --address ":${CA_PORT}" \
  --provisioner-password-file "${PW_FILE}" \
  --output-file "${CA_DIR}/ca.json" || true

echo "[bootstrap-ca] CA bootstrap complete. Root cert: ${CA_DIR}/certs/root_ca.crt"
