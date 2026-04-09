# burritbot Cast Net $ARGUMENTS

Run the live traffic toggle for BurritBot. `$ARGUMENTS` is one of:

- `cast` — route audience traffic through the guarded path
  (`burritbot-net` → NeMo Guardrails → LLM Guard → Envoy → Vertex)
- `recall` — route audience traffic directly to `burritbot-unguarded`
- `status` — show the current route target
- `rehearse` — run the full Act 1 → Act 2 rehearsal sequence

## Preconditions

Before running anything, verify:

1. `scripts/cast-net.sh` exists and is executable
2. `kubectl` is on PATH
3. The current kube-context is the demo cluster:
   ```bash
   kubectl config current-context
   ```
4. The HTTPRoute `burritbot-audience` exists in namespace `burritbot-net`

If any precondition fails, print what is missing and stop. Do not
auto-fix — this command runs on stage, and surprises are worse than
failures.

## Cast / Recall / Status

```bash
./scripts/cast-net.sh $ARGUMENTS
```

Echo the script's output verbatim. If the script exits non-zero,
report the exit code and the last line of output, then stop.

## Rehearse

If `$ARGUMENTS` is `rehearse`, run this sequence:

```bash
./scripts/cast-net.sh status
./scripts/cast-net.sh recall     # start clean: unguarded
echo "Act 1: unguarded. Fire the three attack prompts against" \
     "burritbot-unguarded via the audience frontend."
read -p "Press Enter when Act 1 is done..." _
./scripts/cast-net.sh cast
echo "Act 2: guarded. Fire the same three attack prompts."
read -p "Press Enter when Act 2 is done..." _
./scripts/cast-net.sh status
```

Pause between steps so the operator can watch Grafana's
`cast-net-comparison.json` dashboard update in real time. The two
halves of the dashboard are exactly the pre- and post-cast states.

## Rules

- Never run `cast` on a cluster that is not the demo cluster.
  Double-check the context.
- Never chain `cast` with any other kubectl mutation in the same
  command — the audience should see this one thing happen and
  nothing else.
- If the toggle takes more than 2 seconds, note it — the runbook's
  Pre-flight section has a troubleshooting entry for slow Envoy
  config sync.
