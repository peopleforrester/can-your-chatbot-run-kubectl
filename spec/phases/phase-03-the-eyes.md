# Phase 3: The Eyes (Observability)

**Goal:** Telemetry backbone running — OpenTelemetry Collector with
GenAI semantic conventions, OTel Weaver schema contract,
spinybacked-orbweaver conformance scoring, Prometheus, Grafana, and
the three demo dashboards.

**Inputs:** Phase 2 complete. ArgoCD is syncing, `monitoring`
namespace exists.

**Outputs:**

- `observability/otel-collector/config.yaml` — declares `attributes`
  processor with `gen_ai.provider.name` (canonicalised to `gcp.vertex_ai`
  per OTel semconv v1.37.0), `gen_ai.request.model`,
  `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`; declares
  both `prometheus` and an `otlp*` exporter
- `observability/otel-weaver/genai-semconv-registry.yaml` — Weaver
  registry with a `groups:` key
- `observability/spinybacked-orbweaver/config.yaml` — declares
  `registry:` and `score_threshold:`
- `observability/grafana/dashboards/the-eyes-overview.json`
- `observability/grafana/dashboards/prompt-response-traces.json`
- `observability/grafana/dashboards/cast-net-comparison.json`
- `gitops/apps/otel-collector.yaml`, `gitops/apps/grafana.yaml`,
  `gitops/apps/prometheus.yaml` — ArgoCD Applications with sync-wave `0`

**Test Criteria (tests/test_phase_03_the_eyes.py):**

Static:

- `test_observability_tree_exists`
- `test_otel_collector_has_genai_processors` — all four `gen_ai.*`
  attribute keys present in the `attributes` processor actions list
- `test_otel_collector_exports_prometheus_and_grafana`
- `test_genai_semconv_registry_valid_yaml`
- `test_spinybacked_orbweaver_config_exists`
- `test_three_demo_dashboards_exist` — all three JSON dashboards
  parse as objects with a `title` field

Live:

- `test_otel_collector_pod_running`
- `test_grafana_pod_running`

**Key Technology Decisions:**

- OpenTelemetry Collector 0.149+ (contrib distribution — we need the
  `attributes`, `transform`, and `tail_sampling` processors, plus
  GenAI semconv v1.37.0 support)
- OTel Weaver 0.22+ as the GenAI schema contract
- kube-prometheus-stack for Prometheus + Grafana bundle
- spinybacked-orbweaver as the in-repo conformance scorer; configured
  with a `score_threshold` of 0.85 to make the unguarded path fail
  and the guarded path pass — the audience sees the gap on the
  `cast-net-comparison.json` dashboard

**Known Risk:** The kube-prometheus-stack ServiceMonitor requires the
`prometheus` exporter on port 8889. The collector's default config
does not include this exporter — must be added explicitly in
`observability/otel-collector/config.yaml`.

**Completion Promise:** `<promise>PHASE3_DONE</promise>`

**Skill:** `.claude/skills/the-eyes-otel-genai.md` — read before
editing any file under `observability/`.

**Commits:** 4 expected (OTel collector; Weaver registry; orbweaver;
Grafana dashboards)
