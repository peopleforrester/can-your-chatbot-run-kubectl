# Deinopis — Can Your Chatbot Run kubectl?

Demo platform for the KubeCon NA 2026 talk
**"Can Your Chatbot Run kubectl? Guardrails for LLMs on Kubernetes"**
co-presented by **Whitney Lee** and **Michael Forrester** in Salt Lake City.

## The Name

**Deinopis** is the ogre-faced spider. Unlike most spiders that build a
passive web and wait, Deinopis holds a net between its front legs, watches
with the largest eyes of any spider, and actively casts the net over anything
that walks underneath. That hunting strategy *is* the architecture of this
demo:

- **The Eyes** — OpenTelemetry GenAI semantic conventions + Whitney Lee's
  [spinybacked-orbweaver](https://github.com/wiggitywhitney/spinybacked-orbweaver)
  auto-instrumentation. Everything the platform sees, it sees through the
  eyes.
- **The Net** — NeMo Guardrails + LLM Guard + Envoy AI Gateway + Kyverno +
  Falco. Actively cast over every inference request. Catches what does not
  belong.

Two spiders, two roles, one architecture: spinybacked-orbweaver instruments,
Deinopis enforces. The chatbot itself stays friendly and keeps its name —
**BurritBot** — because the demo opens with the viral Chipotle chatbot
incident (order a burrito, also reverse a linked list in Python).

## The Talk

Two acts, one burrito shop.

- **Act 1 — Unguarded.** BurritBot is deployed to GKE with no protections.
  The audience is invited to break it from their phones: off-topic questions,
  prompt injection, jailbreaks, data extraction, social engineering. It
  complies with all of them. The same pattern that let Chipotle's customer
  support bot explain O(n) linked list reversal happens again, live.
- **Act 2 — Guarded.** The same chatbot runs in a second namespace behind
  the Deinopis net (Envoy AI Gateway → NeMo Guardrails → LLM Guard →
  Vertex AI), with Kyverno policies, Falco AI-workload rules, and OTel GenAI
  semantic conventions wired through to a live Grafana dashboard. The
  audience runs the same attacks and watches them get blocked, logged, and
  traced in real time.

The point: **platform-level governance, not per-developer discipline.** The
platform does the guardrailing, the developer writes a normal Streamlit app.

## Repo Status

**Phase 0 — Bootstrap.** Spec captured, plan drafted, reuse map scoped.
No infrastructure built yet. See `PROJECT_STATE.md` for current state.

## Key Documents

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Claude Code project instructions (read first in every session) |
| `PROJECT_STATE.md` | Current phase and next actions (reconcile at session start) |
| `docs/BUILD-INSTRUCTIONS.md` | Authoritative build spec, preserved verbatim |
| `docs/PLAN.md` | Execution plan, open questions, workflow notes |
| `docs/KUBEAUTO-REUSE-MAP.md` | What to copy/adapt/ignore from the kubeauto-ai-day source |

## Build Phases

1. **GKE Foundation** — Terraform, VPC, Workload Identity Federation
2. **GitOps Bootstrap** — ArgoCD, app-of-apps, sync waves
3. **The Eyes** — Prometheus, Grafana, OTel Collector with GenAI conventions,
   spinybacked-orbweaver
4. **The Net — Security** — Kyverno AI policies, Falco AI rules, SPIFFE/SPIRE
5. **The Net — AI Gateway** — Envoy AI Gateway, NeMo Guardrails, LLM Guard
6. **BurritBot** — Unguarded and guarded Streamlit deployments
7. **Audience Frontend** — Mobile-friendly prompt submission UI + QR code
8. **Hardening** — Full-demo rehearsal, backup videos, cost doc, teardown

Each phase runs in its own Claude Code session. Test-first, ArgoCD-deployed,
no secrets in Git.

## Ancestry

Forked conceptually from [kubeauto-ai-day](https://github.com/peopleforrester/kubeauto-ai-day)
(KubeCon EU 2026 / KubeAuto AI Day, EKS-based IDP). That repo lives on disk
as a local-only reference for this build; see `docs/KUBEAUTO-REUSE-MAP.md`
for exactly what carries forward.

## License

Apache 2.0 (pending) — matching the kubeauto-ai-day lineage.
