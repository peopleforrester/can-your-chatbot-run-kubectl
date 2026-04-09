# Phase 6: BurritBot Application

**Goal:** FastAPI chatbot wrapping Vertex AI `gemini-2.5-flash`,
deployed twice — once in `burritbot-unguarded` (bypasses the gateway)
and once in `burritbot-guarded` (routes through `deinopis-net`). Same
container image for both.

**Inputs:** Phase 5 complete. `deinopis-net` is serving the AI
gateway. `burritbot-unguarded` and `burritbot-guarded` namespaces
exist.

**Outputs:**

- `apps/burritbot/app.py` — FastAPI app; pins `MODEL_NAME` to
  `gemini-2.5-flash`; no references to 1.5 or 2.0 Flash
- `apps/burritbot/requirements.txt` — pinned
- `apps/burritbot/Dockerfile` — two ABOUTME lines at top
- `apps/burritbot/k8s/deployment-unguarded.yaml` — namespace
  `burritbot-unguarded`
- `apps/burritbot/k8s/deployment-guarded.yaml` — namespace
  `burritbot-guarded`, with full `deinopis.io/*` label set
- `apps/burritbot/k8s/service-unguarded.yaml`
- `apps/burritbot/k8s/service-guarded.yaml`
- `gitops/apps/burritbot-unguarded.yaml`, `gitops/apps/burritbot-guarded.yaml`

**Test Criteria (tests/test_phase_06_burritbot.py):**

Static:

- `test_burritbot_tree_exists`
- `test_burritbot_app_pins_gemini_2_5_flash` — string match for the
  correct model, explicit rejection of 1.5 and 2.0 Flash
- `test_burritbot_app_uses_vertex_ai_sdk` — imports `vertexai` or
  `google.cloud.aiplatform`
- `test_burritbot_manifests_present` — four required manifests
- `test_burritbot_unguarded_deployment_valid` — kind Deployment in
  `burritbot-unguarded`
- `test_burritbot_guarded_deployment_has_deinopis_labels` — full
  three-label set on metadata
- `test_burritbot_dockerfile_has_aboutme`

Live:

- `test_unguarded_burritbot_running`
- `test_guarded_burritbot_running`

**Key Technology Decisions:**

- Python 3.13 (matches `pyproject.toml` `requires-python`)
- FastAPI 0.115+, uvicorn for the server
- Vertex AI SDK (`google-cloud-aiplatform` 1.72+); `vertexai.init()`
  inside a lazy cached accessor, not at import time
- `gemini-2.5-flash` — 1.5 is unsupported, 2.0 is deprecated before
  demo day, 3 is preview-tier
- **Same image** for unguarded and guarded; the difference is
  namespace + labels + the gateway route, not the image

**Known Risk:** The Vertex SDK's `usage_metadata` field name differs
between SDK versions. Pin the SDK and test with a live Vertex call
during Phase 6 rehearsal — the OTel gen_ai.* emission depends on
this exact field shape.

**Completion Promise:** `<promise>PHASE6_DONE</promise>`

**Skill:** `.claude/skills/burritbot-vertex-ai.md`

**Commits:** 3 expected (app + Dockerfile; manifests; ArgoCD apps)
