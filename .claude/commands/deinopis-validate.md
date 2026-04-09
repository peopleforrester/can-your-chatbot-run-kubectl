# Deinopis Validate $ARGUMENTS

Run the validation loop for the Deinopis build. `$ARGUMENTS` is either
a phase number (`3`, `4`, …, `8`) or `all` to validate every phase.

## Static validation (always runs)

```bash
uv run pytest -q -m static
```

This is the offline-safe baseline. No cluster, no GCP auth. Every
static test should be either green or explicitly red-for-a-reason.

## Phase-scoped static validation

If `$ARGUMENTS` is a number:

```bash
uv run pytest -q -m phase$ARGUMENTS -m static -v
```

## Live validation (only if kubeconfig + GCP auth are available)

```bash
# Check that a kubeconfig is present
kubectl config current-context || {
  echo "No kubeconfig; skipping live tests"; exit 0;
}

# Check that GCP ADC is present
gcloud auth application-default print-access-token >/dev/null 2>&1 || {
  echo "No GCP ADC; skipping GCP-backed tests"; exit 0;
}

uv run pytest -q -m live
```

Live tests pytest-skip themselves when the cluster or credentials are
not available — this is expected behaviour in offline-authoring
sessions.

## Extra per-layer checks

### The Eyes

```bash
yamllint observability/
jq empty observability/grafana/dashboards/*.json
```

### The Net — Security

```bash
yamllint security/
kyverno test security/kyverno/tests/
```

### The Net — AI Gateway

```bash
yamllint ai-gateway/
```

### Scripts

```bash
shellcheck scripts/*.sh
```

## Reporting

At the end, print:

- Number of static tests passed / failed / skipped
- Number of live tests passed / failed / skipped
- Per-layer lint results (one line each)
- Whether the working tree is clean (`git status --porcelain`)

Do not commit, do not push. This is a read-only health check.
