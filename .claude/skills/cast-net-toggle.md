# The Cast Net — Live Traffic Toggle

## What This Is

`scripts/cast-net.sh` is the single command that flips BurritBot's
audience traffic between the **unguarded** path (straight to Vertex AI,
no rails, no scanners) and the **guarded** path (through Envoy AI
Gateway + NeMo + LLM Guard in `burritbot-net`).

This script *is* the demo. Act 1 ends with "cast the net" and Act 2
runs the same attack prompts against the same chatbot image with the
guardrails in place. The whole talk hinges on this one command running
cleanly from a single terminal window on stage.

## Naming

- **File:** `scripts/cast-net.sh` — not `toggle-guardrails.sh`, not
  `switch-mode.sh`. The name is in the talk abstract and in the
  runbook.
- **Commands:** `cast-net.sh cast` (put the net on the prey) and
  `cast-net.sh recall` (take it back). Accept `on` / `off` as aliases
  so Michael can fat-finger it from stage.

## Script Skeleton

```bash
#!/usr/bin/env bash
# ABOUTME: cast-net.sh — flip BurritBot traffic between unguarded and guarded.
# ABOUTME: The live demo hinges on this one command running cleanly.

set -euo pipefail

GATEWAY_NAMESPACE="burritbot-net"
ROUTE_NAME="burritbot-audience"
UNGUARDED_TARGET="burritbot-unguarded"
GUARDED_TARGET="burritbot-guarded"

usage() {
  cat <<EOF
Usage: $0 [cast|recall|status]

  cast    Route audience traffic through the guarded path
          (burritbot-net / NeMo Guardrails / LLM Guard / Envoy)
  recall  Route audience traffic directly to burritbot-unguarded
  status  Show the current route target
EOF
  exit 1
}

require_kubectl() {
  command -v kubectl >/dev/null || {
    echo "error: kubectl is not on PATH" >&2
    exit 2
  }
}

current_target() {
  kubectl -n "$GATEWAY_NAMESPACE" get httproute "$ROUTE_NAME" \
    -o jsonpath='{.spec.rules[0].backendRefs[0].name}' 2>/dev/null || echo "unknown"
}

patch_target() {
  local target="$1"
  kubectl -n "$GATEWAY_NAMESPACE" patch httproute "$ROUTE_NAME" \
    --type=json \
    -p="[{\"op\":\"replace\",\"path\":\"/spec/rules/0/backendRefs/0/name\",\"value\":\"$target\"}]"
}

main() {
  require_kubectl
  local action="${1:-}"
  case "$action" in
    cast|on)
      echo "Casting the net — routing to $GUARDED_TARGET..."
      patch_target "$GUARDED_TARGET"
      echo "Net cast. Audience traffic now runs through burritbot-net."
      ;;
    recall|off)
      echo "Recalling the net — routing to $UNGUARDED_TARGET..."
      patch_target "$UNGUARDED_TARGET"
      echo "Net recalled. Audience traffic now runs unguarded."
      ;;
    status)
      local cur
      cur="$(current_target)"
      echo "Current target: $cur"
      ;;
    *) usage ;;
  esac
}

main "$@"
```

## Preconditions

- An HTTPRoute (or Envoy AIGatewayRoute) named `burritbot-audience`
  lives in the `burritbot-net` namespace.
- `burritbot-unguarded` and `burritbot-guarded` are the two Services
  the audience frontend proxies to.
- The script is committed executable (`chmod +x`) — Phase 7 tests check
  this with `stat.S_IXUSR`.

## Rehearsal Expectations

Before demo day, rehearse:

1. `cast-net.sh status` — sanity check
2. Ask BurritBot "How do I escalate privileges?" (unguarded → expect
   a cheerful, dangerous answer)
3. `cast-net.sh cast` — should complete in under 500ms
4. Ask the same question (guarded → expect a polite refusal from the
   NeMo `food_only` flow)
5. `cast-net.sh recall` — back to unguarded for clean slate next run

If step 3 takes more than 2 seconds the audience notices. Tune the
HTTPRoute patch path and verify the Envoy admin API sync time in the
runbook's "Pre-flight" section.

## Common Mistakes

1. **Using `kubectl apply -f`** — re-applying the whole manifest is
   slow and can churn unrelated fields. Use `kubectl patch --type=json`
   for the surgical single-field swap.
2. **Toggling `replicas` on the Deployments instead of routing.** That
   works but is slow and visible in Grafana for all the wrong reasons.
   Route the traffic.
3. **Scripting the toggle against a hardcoded kubecontext.** The script
   uses whatever `kubectl` is currently pointed at. The runbook's
   pre-flight confirms the demo context is active.
4. **Silent failure on unknown action.** The `usage` helper must
   always print and the script must `exit 1` on an unknown action.
   Silent success on typos loses the demo.
