#!/usr/bin/env bash
# ABOUTME: Toggles live audience traffic between the unguarded and guarded BurritBot.
# ABOUTME: Patches the audience-frontend Deployment's BURRITBOT_TARGET env var in place.
set -euo pipefail

SCRIPT_NAME="cast-net"
NAMESPACE="audience"
DEPLOYMENT="audience-frontend"
CONTAINER="audience-frontend"
ENV_VAR="BURRITBOT_TARGET"
UNGUARDED="burritbot-unguarded"
GUARDED="burritbot-guarded"

usage() {
  cat <<EOF
Usage: ${SCRIPT_NAME} <cast|recall|status>

  cast     Route audience traffic through the burritbot-net guarded path (${GUARDED}).
  recall   Route audience traffic directly to the unguarded BurritBot (${UNGUARDED}).
  status   Print the current BURRITBOT_TARGET without changing anything.

Rehearsal expectation: the toggle must land under 500ms on a warm cluster.
This script never uses 'kubectl apply' — it patches the running Deployment
with a JSON patch so ArgoCD does not race it.
EOF
}

require_kubectl() {
  if ! command -v kubectl >/dev/null 2>&1; then
    echo "${SCRIPT_NAME}: kubectl not on PATH" >&2
    exit 2
  fi
}

current_target() {
  kubectl -n "${NAMESPACE}" get deploy "${DEPLOYMENT}" \
    -o jsonpath="{.spec.template.spec.containers[?(@.name=='${CONTAINER}')].env[?(@.name=='${ENV_VAR}')].value}"
}

patch_target() {
  local target="$1"
  # Find the env var's index in the container spec so we can patch in place.
  local idx
  idx=$(kubectl -n "${NAMESPACE}" get deploy "${DEPLOYMENT}" -o json \
    | python3 -c '
import json, sys
doc = json.load(sys.stdin)
containers = doc["spec"]["template"]["spec"]["containers"]
for c in containers:
  if c["name"] == "'"${CONTAINER}"'":
    for i, e in enumerate(c.get("env", [])):
      if e["name"] == "'"${ENV_VAR}"'":
        print(i)
        sys.exit(0)
sys.exit(1)
')

  kubectl -n "${NAMESPACE}" patch deploy "${DEPLOYMENT}" \
    --type=json \
    -p="[{\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/env/${idx}/value\",\"value\":\"${target}\"}]"
}

main() {
  local action="${1:-}"
  require_kubectl

  case "${action}" in
    cast)
      echo "${SCRIPT_NAME}: casting The Net — switching ${DEPLOYMENT} to ${GUARDED}"
      patch_target "${GUARDED}"
      ;;
    recall)
      echo "${SCRIPT_NAME}: recalling The Net — switching ${DEPLOYMENT} to ${UNGUARDED}"
      patch_target "${UNGUARDED}"
      ;;
    status)
      local current
      current=$(current_target || echo "<unset>")
      echo "${SCRIPT_NAME}: current ${ENV_VAR}=${current}"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
