# The Eyes — OTel Collector with GenAI Semantic Conventions

## Version Pins

- OpenTelemetry Collector: **0.149+** (contrib distribution — we need the
  `attributes`, `transform`, and `tail_sampling` processors, plus
  GenAI semantic conventions v1.37.0 support)
- OTel Weaver: **0.22+**
- Prometheus: via `kube-prometheus-stack` (monitoring namespace)
- Grafana: bundled with `kube-prometheus-stack`

## The Point of This Skill

The whole "Eyes" story is this: **if BurritBot's LLM calls are not
tagged with `gen_ai.*` attributes, Grafana cannot show the cost of being
wrong, and the audience cannot see the difference between unguarded and
guarded runs.** OTel Weaver is the schema contract that makes those
attributes consistent across Python SDK, Envoy AI Gateway, NeMo
Guardrails, and LLM Guard.

## Required GenAI Attributes

Every span and metric from BurritBot, NeMo, LLM Guard, and Envoy must
carry at minimum:

| Attribute | Example | Source |
|-----------|---------|--------|
| `gen_ai.provider.name` | `"gcp.vertex_ai"` | Instrumentation |
| `gen_ai.request.model` | `"gemini-3-pro"` | Instrumentation |
| `gen_ai.usage.input_tokens` | `213` | Vertex response |
| `gen_ai.usage.output_tokens` | `87` | Vertex response |
| `burritbot.layer` | `"the-net"` \| `"the-eyes"` \| `"the-web"` | Resource attribute |
| `burritbot.guarded` | `true` \| `false` | Resource attribute |

The Weaver registry (`observability/otel-weaver/genai-semconv-registry.yaml`)
declares these as required. CI runs `weaver registry check` to enforce.

## Collector Config Shape

`observability/otel-collector/config.yaml` must contain **all** of:

```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }

processors:
  memory_limiter:          # MUST be first in every pipeline
    check_interval: 1s
    limit_mib: 400
  batch:
    timeout: 5s
    send_batch_size: 1024
  attributes:              # gen_ai.* enforcement (semconv v1.37.0)
    actions:
      - key: gen_ai.provider.name
        action: upsert
      - key: gen_ai.request.model
        action: upsert
      - key: gen_ai.usage.input_tokens
        action: upsert
      - key: gen_ai.usage.output_tokens
        action: upsert
  resource:
    attributes:
      - { key: burritbot.layer, value: the-eyes, action: upsert }

exporters:
  prometheus:              # serves /metrics for the kube-prometheus-stack scraper
    endpoint: 0.0.0.0:8889
  otlp/grafana:            # traces to Grafana Tempo or Grafana Cloud OTLP endpoint
    endpoint: tempo.monitoring.svc.cluster.local:4317
    tls: { insecure: true }

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, attributes, resource, batch]
      exporters: [otlp/grafana]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, attributes, resource, batch]
      exporters: [prometheus]
```

Phase 3 tests check for:
1. The `attributes` processor declares actions for every key in
   `GEN_AI_ATTRIBUTES`
2. Both a `prometheus` exporter and an `otlp*` exporter exist
3. The Weaver registry parses as YAML and contains a `groups:` key
4. `observability/spinybacked-orbweaver/config.yaml` exists and declares
   both `registry:` and `score_threshold:`

## spinybacked-orbweaver

This is the in-repo auto-instrumentation scorer. It ingests live
telemetry, compares each span against the Weaver registry, and emits a
conformance score (0.0-1.0) that Grafana plots against the two BurritBot
namespaces. Configuration lives in
`observability/spinybacked-orbweaver/config.yaml`:

```yaml
# ABOUTME: spinybacked-orbweaver config — scores incoming spans against
# ABOUTME: the OTel Weaver GenAI registry and exports a conformance metric.
registry: /etc/weaver/genai-semconv-registry.yaml
score_threshold: 0.85
watch_namespaces:
  - burritbot-unguarded
  - burritbot-guarded
  - burritbot-net
```

The threshold is the floor that "The Eyes" alert on. Unguarded
BurritBot almost always scores below 0.85 because the raw Python client
does not emit `gen_ai.usage.*`. The guarded path scores above 0.85
because Envoy AI Gateway adds the tokens on egress. That gap is the
punch line of Act 2.

## The Three Demo Dashboards

`observability/grafana/dashboards/` must contain exactly these three
JSON files (Phase 3 tests enforce names):

1. `the-eyes-overview.json` — orbweaver conformance score, span rate,
   error rate by namespace
2. `prompt-response-traces.json` — table view of Vertex prompts and
   responses with `gen_ai.*` attributes as columns
3. `cast-net-comparison.json` — side-by-side of burritbot-unguarded vs
   burritbot-guarded on the same time range (this is the slide)

## Common Mistakes

1. **`memory_limiter` not first.** Always first processor in every
   pipeline.
2. **Missing `prometheus` exporter.** The kube-prometheus-stack ServiceMonitor
   scrapes the exporter on port 8889. Without it metrics never leave
   the collector.
3. **Hardcoding `gen_ai.request.model` to a string.** It must come from
   the actual SDK call — see `burritbot-vertex-ai.md` for how to emit
   it from the Python client.
4. **Using `prometheusremotewrite` instead of `prometheus`.** We are
   running kube-prometheus-stack with a ServiceMonitor. Remote write is
   the wrong pattern for this install.
5. **Weaver registry file but no `groups:`.** Weaver silently no-ops
   without a group. Phase 3 test catches this.
