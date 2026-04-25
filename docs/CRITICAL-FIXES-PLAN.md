# Critical Fixes Plan — burritbot
# Source: senior-review findings (post-Phase-8). Strict TDD, phase by phase.

## Verification Method
Findings re-checked against actual repo state on `staging` branch before
this plan was written. Conversation-time test counts and file contents
were verified by direct file reads, not from PROJECT_STATE summaries.

## Verified Critical Findings

| ID  | Finding                                                                                                                                      | Verified |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| C1  | All 5 ArgoCD apps in `gitops/apps/*.yaml` reference `deploy/<x>` paths; no `deploy/` directory exists. App-of-apps will fail on first sync.  | Yes      |
| C2  | Pods declare `serviceAccountName: burritbot` and `audience-frontend`; no `ServiceAccount` manifests exist anywhere. Pods cannot start.       | Yes      |
| C3  | `ai-gateway/nemo-guardrails/config.yaml` sets `colang_version: "2.x"`; all four `.co` rails use Colang 1.0 syntax. Rails will refuse to load. | Yes     |
| C4  | `apps/burritbot/app.py` ships `opentelemetry-instrumentation-fastapi` but never calls `FastAPIInstrumentor.instrument_app(app)`. Unguarded deployment has zero `OTEL_*` env vars. No traces will reach the collector; the cast-net comparison dashboard will be half-empty. | Yes |
| C5  | `PROJECT_STATE.md` line 66 claims "51 static tests"; actual is 75 collected / 59 static passing. State file is stale.                        | Yes      |
| C9  | `apps/audience-frontend/k8s/deployment.yaml` references image `audience-frontend:0.1.0`; no Dockerfile exists at `apps/audience-frontend/backend/Dockerfile`. Image cannot be built. | Yes |

(Numbers reflect the senior review's IDs, not a new numbering.)

## Out of Scope for This Plan
Deferred (require live container/cluster or larger surface):
- C3 verification against a running NeMo Guardrails 0.11 container
- C7 (CORS `allow_origins=["*"]`)
- C8 (per-pod rate limiter)
- C10 (cast-net.sh container-index hardcode)
- C11 (Terraform GCS backend)
- C12 (private cluster)
- C13 (`deletion_protection = false`)
- All Medium/Low items (#14–#27)
- Missing AI Gateway / NeMo / LLM Guard / OTel Collector Deployment
  manifests (deeper structural gap than the review noted; tracked as a
  follow-up below)

## Newly Surfaced Gap (not in review)
The `ai-gateway/`, `observability/otel-collector/`, and
`security/falco/rules/` directories ship config files but no
Kubernetes `Deployment`, `DaemonSet`, or `ConfigMap`-wrap manifests.
ArgoCD `path:` will resolve to a directory with no applicable resources.
This is captured here for follow-up but not fixed in this pass — the
ArgoCD path resolution test in Phase A1 will accept "directory exists
and contains at least one yaml" rather than gating on deployable
content.

## Plan (No Timelines)

Each phase follows the project's 5-step TDD protocol: write failing
test → confirm fail (not import error) → minimal implementation →
confirm pass → refactor if needed → commit on `staging`.

### Phase A1 — ArgoCD path resolution (C1)

**Test:** `tests/test_critical_fix_a1_argocd_paths.py`

Asserts every `gitops/apps/*.yaml` Application's `spec.source.path:` (or
`spec.source.repoURL` chart for Helm-source apps) resolves to a real
directory under the repo root that contains at least one yaml file.

**Implementation:** Create `deploy/<component>/kustomization.yaml` for
each of `burritbot`, `audience`, `monitoring`, `security`, `ai-gateway`.
Each kustomization references the corresponding existing manifests via
relative `resources:` paths. Where no deployable Kubernetes manifests
exist yet (ai-gateway, monitoring deployment, falco-rule ConfigMap),
the kustomization includes an explicit `# TODO:` placeholder commented
into a stub yaml that documents the missing piece. Test passes when
`deploy/<x>/` exists and contains at least one yaml file.

The `00-namespaces.yaml` Application uses `path: gitops/namespaces`
which also does not exist — A1 covers it the same way, by creating
`gitops/namespaces/` with a `Namespace` manifest per known namespace
(`monitoring`, `security`, `burritbot-unguarded`, `burritbot-guarded`,
`burritbot-net`, `audience`).

### Phase A2 — ServiceAccount manifests (C2)

**Test:** `tests/test_critical_fix_a2_service_accounts.py`

For every `serviceAccountName:` referenced in any
`apps/**/k8s/*deployment*.yaml`, assert a `kind: ServiceAccount`
manifest with the same `name` and `namespace` exists somewhere under
`apps/<component>/k8s/`. For the `burritbot` SA in
`burritbot-guarded`, additionally assert presence of the
`iam.gke.io/gcp-service-account` annotation matching the WIF binding
in `infrastructure/terraform/iam.tf:55`.

**Implementation:**
- `apps/burritbot/k8s/serviceaccount-burritbot-guarded.yaml`
  — `ServiceAccount/burritbot` in `burritbot-guarded` with WIF annotation
- `apps/burritbot/k8s/serviceaccount-burritbot-unguarded.yaml`
  — `ServiceAccount/burritbot` in `burritbot-unguarded` (no WIF; the
  unguarded path uses a direct call but still needs an SA to exist)
- `apps/audience-frontend/k8s/serviceaccount.yaml`
  — `ServiceAccount/audience-frontend` in `audience`

The WIF annotation value is left as `REPLACE_WITH_WORKLOAD_GSA_EMAIL`
to match the existing pattern of placeholder values throughout the
manifests (see `REPLACE_WITH_PROJECT` in deployment images).

### Phase A3 — audience-frontend Dockerfile (C9)

**Test:** `tests/test_critical_fix_a3_audience_dockerfile.py`

Asserts `apps/audience-frontend/backend/Dockerfile` exists, starts
with two `# ABOUTME:` lines, runs as non-root user 1001, and exposes
port 8080 — same pattern as `apps/burritbot/Dockerfile`.

**Implementation:** Mirror `apps/burritbot/Dockerfile`. Create a
`requirements.txt` next to `main.py` listing the exact deps the audience
backend imports (`fastapi`, `uvicorn[standard]`, `httpx`, `pydantic`,
`slowapi`).

### Phase A4 — Colang version alignment (C3)

**Test:** `tests/test_critical_fix_a4_colang_alignment.py`

Loads `ai-gateway/nemo-guardrails/config.yaml`, reads
`colang_version`, then scans every `.co` file under
`ai-gateway/nemo-guardrails/rails/` for tokens that are unique to one
syntax. Asserts the syntax matches the declared version.

Colang 1.0 markers: `define user`, `define bot`, `flow ` followed by
prose, `abort`. Colang 2.0 markers: `flow user expressed`, `await`,
`user said "..."`, `match`.

**Implementation:** Change `colang_version: "2.x"` → `"1.0"`. The
existing rails are 1.0 syntax — minimal change, matches what's
authored. Add a comment noting that live verification against a NeMo
Guardrails 0.11 container is still required (deferred per scope).

### Phase A5 — OTel instrumentation wiring (C4)

**Tests:**
- `tests/test_critical_fix_a5_otel_app_wired.py` — imports
  `apps.burritbot.app`, asserts `FastAPIInstrumentor`'s
  `_is_instrumented_by_opentelemetry` attribute is set on the FastAPI
  app instance after `create_app()`.
- `tests/test_critical_fix_a5_otel_unguarded_env.py` — parses
  `apps/burritbot/k8s/deployment-unguarded.yaml` and asserts the
  container has `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME`
  env vars (with `OTEL_SERVICE_NAME=burritbot-unguarded`).

**Implementation:**
- `apps/burritbot/app.py`: add `FastAPIInstrumentor.instrument_app(app)`
  inside `create_app()` after route registration. Import lazily to
  keep the module importable without OTel installed in test envs that
  may strip dev deps.
- `apps/burritbot/k8s/deployment-unguarded.yaml`: add the two `OTEL_*`
  env vars matching the guarded deployment's pattern.

### Phase A6 — PROJECT_STATE.md test count refresh (C5)

**Test:** `tests/test_critical_fix_a6_project_state_truthful.py`

Reads `PROJECT_STATE.md`, extracts the asserted total static test
count, and asserts it equals the actual `pytest -m static --collect-only`
count. This makes future state drift fail the suite.

**Implementation:** Update `PROJECT_STATE.md` with the actual count
*after* phases A1–A5 land (they each add a test, so the final number
is computed at the end). Add a "Verification Method" header to
PROJECT_STATE per `~/.claude/rules/state-persistence.md`.

## Commit Strategy
- One commit per phase on `staging`. Run the full static test suite
  before each commit. Do not proceed to the next phase if any test
  fails.
- Each commit message names the fix ID (e.g., `fix(C1): resolve ArgoCD
  app paths to real directories`).
- After A6, run the full static suite once more, then merge `staging`
  into `main` per the project's autonomous staging→main workflow.

## Exit Conditions
- All six tests added in this plan pass.
- Total static test count: 59 + 6 = 65 (assuming no incidental
  additions).
- `PROJECT_STATE.md` reflects the new count, names this plan, and
  marks each fix as Verified-Static / Pending-Live as appropriate.
- The deferred items (Colang live verification, missing
  Deployment manifests for ai-gateway/monitoring, all Medium/Low
  review items) are listed in `PROJECT_STATE.md` as known gaps.
