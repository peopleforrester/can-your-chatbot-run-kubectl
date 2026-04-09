# Deinopis Architecture — Skill File

## What Deinopis Is

Deinopis is the platform name for this build. It is named for the
ogre-faced spider (genus *Deinopis*) — a nocturnal hunter that does not
spin a passive web. Instead it weaves a small, stretchy cast net between
its front legs, watches the ground with enormous reflective eyes, and
throws the net over any prey that walks underneath.

That is exactly the operational model for guarding a chatbot that can
touch Kubernetes.

| Metaphor | Reality |
|----------|---------|
| **The Eyes** | OpenTelemetry Collector + OTel Weaver + spinybacked-orbweaver + Prometheus + Grafana |
| **The Net**  | NeMo Guardrails + LLM Guard + Envoy AI Gateway + Kyverno + Falco |
| **The Web**  | SPIFFE/SPIRE + Gateway API + ArgoCD + cert-manager + External Secrets |

The talk demo itself is called **BurritBot**. BurritBot keeps its friendly
name because the narrative opens with the 2025 Chipotle viral chatbot
incident — the chatbot that answered "Which burrito is best?" with a
cheerful response, and then answered "How do I escalate privileges in
our cluster?" with an equally cheerful response.

## Non-Negotiable Architecture Decisions

| Decision | Why it matters |
|----------|----------------|
| **GKE Standard with Node Auto-Provisioning** — *not* Autopilot | Autopilot disables privileged DaemonSets. Falco cannot run on Autopilot. Without Falco there is no runtime detection layer for The Net. |
| **Workload Identity Federation**, no service-account JSON keys | Every rule in this repo fails explicitly when a JSON key is present. Rotate via GCP, not via Git. |
| **Vertex AI with `gemini-3-pro`** | 1.5 is unsupported; 2.0 already retired; 2.5 Flash/Pro retire 2026-10-16 (before demo day); 3 Flash is preview. 3 Pro is the only GA model guaranteed to be live during the November 2026 talk. Access via `google-genai` (`vertexai.generative_models` is removed after 2026-06-24). |
| **`deinopis-net` namespace** (not `guardrails`) | The guarded path runs here. The name is load-bearing — Kyverno policies, NetworkPolicies, and tests all reference it literally. |
| **`deinopis-*` container naming** | Kyverno enforces that every guardrail sidecar has a name starting with `deinopis-`. This is how operators tell at a glance which containers are part of The Net vs. part of the application. |
| **`deinopis.io/*` label set** | Every Deployment / Pod / Job in BurritBot namespaces must carry `deinopis.io/layer`, `deinopis.io/model-source`, and `deinopis.io/model-hash`. Kyverno enforces; Grafana dashboards group on these. |
| **`cast-net.sh` toggle** | The live demo flips the gateway route from `burritbot-unguarded` to `burritbot-guarded` with a single script. The script is the demo. |

## Phase Order

1. **Foundation** — GKE Standard + NAP, VPC, WIF, Secret Manager
2. **GitOps** — ArgoCD, app-of-apps, namespaces
3. **The Eyes** — OTel Collector with `gen_ai.*` processors, Weaver registry, spinybacked-orbweaver, Prometheus, Grafana dashboards
4. **The Net — Security** — Kyverno chart 3.7.1 (app 1.17+) CEL policies, Falco 0.43.x with rules `required_engine_version: 0.57.0` on modern-bpf
5. **The Net — AI Gateway** — NeMo Guardrails Colang rails, LLM Guard input/output scanners, Envoy AI Gateway route
6. **BurritBot** — FastAPI app, Vertex AI client, unguarded + guarded Deployments
7. **Audience Frontend** — FastAPI + rate limiting, `cast-net.sh` toggle, QR code for the room
8. **Hardening** — Runbook, scorecard, teardown script, final rehearsal

Phases 3-5 are the whole point of the talk. Phase 1-2 are table stakes.
Phases 6-7 are the demo surface. Phase 8 is the pre-flight.

## How Skills Plug In

Read the matching skill file **before** generating any config for a
component:

- `the-eyes-otel-genai.md` — before touching observability/
- `the-net-kyverno-deinopis.md` — before touching security/kyverno/
- `the-net-ai-gateway.md` — before touching ai-gateway/
- `burritbot-vertex-ai.md` — before touching apps/burritbot/
- `cast-net-toggle.md` — before touching scripts/cast-net.sh

If a skill is missing for a component you are about to build, stop and
write the skill first. The skill file is where we capture "what the
training data gets wrong about this tool."

## Honesty

The scorecard in `docs/SCORECARD.md` records which layers actually fired
during rehearsals. Update it honestly. A red cell is more useful to the
audience than a cheerful green one that lies.
