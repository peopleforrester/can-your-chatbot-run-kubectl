# Full Plan — Burrito Bots to Guardrails

Execution plan for the KubeCon NA 2026 demo platform. The authoritative spec
is `BUILD-INSTRUCTIONS.md` (preserved verbatim); this file is the *plan* on
top of it: what we'll actually do, in what order, with what reuse, and what
decisions remain open.

---

## 1. Talk Framing

- **Title:** "Can Your Chatbot Run kubectl? Guardrails for LLMs on Kubernetes"
- **Event:** KubeCon NA 2026, Salt Lake City
- **Speakers:** Michael Forrester, Whitney Lee
- **Duration:** ~30 minutes (demo runs in ≤25, leaving ~5 for Q&A)
- **Thesis:** Platform-level governance (policy + runtime + gateway + OTel)
  beats per-developer discipline. The same app, deployed twice, behaves
  completely differently based on the platform it's deployed *on*.
- **Audience interaction:** Scan a QR code, submit prompts from their phones,
  watch the guarded vs unguarded side-by-side on a projector.

## 2. Architecture at a Glance

```
┌──────────────────────────── GKE (us-west1) ────────────────────────────┐
│                                                                         │
│   Namespaces                                                            │
│   ──────────                                                            │
│   argocd              monitoring         security                       │
│   guardrails          burritbot-unguarded  burritbot-guarded            │
│   audience                                                              │
│                                                                         │
│   UNGUARDED path:                                                       │
│     audience-frontend ──► burritbot-unguarded ──► Vertex AI (direct)    │
│                                                                         │
│   GUARDED path:                                                         │
│     audience-frontend                                                   │
│        └─► burritbot-guarded ──► Envoy AI Gateway                       │
│                                      └─► NeMo Guardrails (Colang)      │
│                                      └─► LLM Guard (scanners)          │
│                                      └─► Vertex AI                     │
│                                                                         │
│   Cross-cutting:                                                        │
│     • Kyverno (AI workload policies, sidecar enforcement, provenance)  │
│     • Falco (AI-workload runtime rules, shell detection, egress watch)│
│     • OTel Collector with gen_ai.* semantic conventions                │
│     • Prometheus + Grafana (3 dashboards for the demo)                  │
│     • External Secrets Operator ← GCP Secret Manager                    │
│     • ArgoCD app-of-apps with sync waves                                │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3. Phase-by-Phase Plan

One Claude Code session per phase. Each session starts by reading
`CLAUDE.md`, `PROJECT_STATE.md`, and the relevant sections of
`BUILD-INSTRUCTIONS.md`. Each phase is TDD: write tests first, then make
them pass. Each phase ends with a staging commit and a staging→main merge
once tests are green.

| # | Phase | Budget | Key deliverables | Kubeauto reuse |
|---|-------|--------|------------------|----------------|
| 1 | GKE Foundation | 90 min | Terraform: VPC, GKE (Standard + NAP), WIF, Secret Manager, namespaces | Terraform *structure* only; rewrite all resources for GCP |
| 2 | GitOps Bootstrap | 60 min | ArgoCD install, app-of-apps root, sync wave plan | Reuse app-of-apps pattern, RBAC, sync-wave convention |
| 3 | Observability | 90 min | Prom + Grafana + OTel Collector with gen_ai.* processors; 3 dashboards; spinybacked-orbweaver auto-instrumentation | Reuse OTel wiring skill and base values; extend with GenAI conventions |
| 4 | Security | 120 min | Kyverno AI policies (provenance, sidecar, OTel annotations), Falco AI-workload rules, network policies | Reuse disallow-privileged, require-labels, require-resource-limits, require-probes, default-deny; extend falco base rules |
| 5 | AI Gateway | 120 min | Envoy AI Gateway, NeMo Guardrails (Colang), LLM Guard (input+output scanners) | None — all new |
| 6 | BurritBot | 90 min | Streamlit app (Dockerfile, app.py, system prompt), unguarded + guarded deployments | None — all new |
| 7 | Audience Frontend | 60 min | Mobile web UI, QR code, WebSocket, FastAPI/Node proxy, rate limiting | None — all new |
| 8 | Hardening | 60 min | RUNBOOK.md, toggle-guardrails.sh, backup videos, COST.md, TEARDOWN.md | Reuse COST/TEARDOWN document *structure* |

**Total wall-clock budget:** ~11 hours of AI build time. Realistic real-world
spread: several working sessions plus full rehearsals in Phase 8.

## 4. Reuse Strategy

The kubeauto-ai-day tree lives on disk at
`~/repos/kubecon/2026_Kubecon_North_America_CNCF_Can_Your_Chatbot_Run_Kubectl/kubeauto-ai-day/`
and is **gitignored** here. Every session that needs to reuse a file reads
it from that path directly.

See `KUBEAUTO-REUSE-MAP.md` for the per-file decision matrix (copy / adapt /
extend / ignore). Highlights:

- **Copy-with-rename to GKE context:** `.claude/commands/build-phase.md`,
  `.claude/commands/validate-phase.md`, `.claude/skills/argocd-patterns.md`,
  `gitops/bootstrap/app-of-apps.yaml`, several Kyverno policies, the tests/
  helper structure.
- **Adapt (EKS → GKE substitution):** ArgoCD `values.yaml` (ALB → Gateway API),
  Falco install (must work on GKE Standard + NAP), External Secrets
  configuration (AWS SM → GCP SM).
- **Extend (base + AI-specific additions):** Kyverno policies (add AI sidecar,
  model provenance, OTel annotations), Falco rules (add AI workload rules),
  OTel collector (add GenAI semconv processors).
- **Do not reuse:** `infrastructure/terraform/*` (rewrite for GCP), Backstage,
  Crossplane, EKS addons, any AWS IAM / IRSA / ACM references.

## 5. Staging → Main Workflow (autonomous)

Per global rule:
1. Work on `staging`. Main is protected on the remote.
2. After each logical unit of work: `git add`, commit on staging, run tests,
   push staging, merge staging→main, push main. No confirmation requests.
3. Commit messages are professional and technical. No AI / Claude references.

**Bootstrap exception (Phase 0 only):** the very first commit creates `main`
from scratch because `staging` cannot exist without it. After the bootstrap,
`staging` becomes the working branch for all phases.

## 6. Critical Versions (pin, do not use latest)

From the spec:
- GKE: 1.30+ (DRA support)
- ArgoCD: 2.14+
- Kyverno: 1.13+ (CEL policies GA)
- Falco: 0.40+ (modern-bpf driver)
- OTel Collector: 0.100+ (GenAI semantic conventions support)
- OTel Weaver: 0.16+ (registry check, emit, live-check)
- NeMo Guardrails: 0.11+
- LLM Guard: 0.3.17+
- Grafana: 11+
- spinybacked-orbweaver: latest (Whitney's agent)

Every Phase-X session must verify the relevant version is still current
(GitHub releases + official docs) before writing chart values. The
kubeauto-ai-day `docs/VERSION-MAP.md` is a good cross-check for shared
components — but the deployed versions there drifted between build and talk,
so prefer live-check over stale map.

## 7. Open Decisions (resolve before or during Phase 1)

1. **GCP project ID.** Spec suggests `burritbot-kubecon-2026`. Confirm or
   provide real ID. Needed for Terraform variables and Vertex AI routing.
2. **Autopilot vs Standard.** Spec defaults to Autopilot, Phase 4 risk note
   recommends Standard with NAP for Falco DaemonSet support. **Recommended:
   GKE Standard + node auto-provisioning.** Confirm in Phase 1.
3. **Region.** Spec suggests `us-west1` (close to SLC). Verify Vertex AI
   availability for the chosen Gemini model (Flash vs Pro).
4. **Gemini model choice.** `gemini-1.5-flash` in the sample app, but 1.5
   may be deprecated by the talk date. Use the latest Flash GA at build time.
5. **Audience frontend backend language.** Spec says "Node.js or Python
   FastAPI." Default to **FastAPI** to match the Python-first convention
   of the rest of the stack and minimize container images.
6. **Licensing.** kubeauto-ai-day is Apache 2.0. Keep the same license here
   unless there's a reason not to.
7. **Demo domain / Cloud DNS.** Optional in the spec. Decide whether to
   route the audience frontend through a pretty hostname or just use the
   Gateway IP.
8. **GitHub repo visibility timing.** Already decided public at init. If
   something in the guardrails config ends up sensitive (unlikely), flip to
   private until the talk.

## 8. Risk Register

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Falco cannot run on GKE Autopilot (DaemonSet / privileged restriction) | High | Switch to GKE Standard + NAP in Phase 1 (pre-emptive) |
| OTel GenAI semantic conventions still shifting | Medium | Pin OTel Collector ≥0.100 and verify the `gen_ai.*` namespace on the day we write the config |
| spinybacked-orbweaver is a moving target | Medium | Pin the exact commit used for rehearsal; document in `observability/spinybacked-orbweaver/config.yaml` |
| Vertex AI rate limiting during audience interaction | Medium | Rate-limit the audience frontend at 10 req/min/IP; also pre-warm a small response cache |
| Conference WiFi unreliable | High | Pre-record backup videos for every demo segment in Phase 8; have a cellular hotspot on standby |
| Cluster left running between rehearsals | Medium | `demo/teardown.sh` + nightly Terraform destroy reminder |
| Secrets accidentally committed | Low | gitleaks pre-commit hook (port from kubeauto-ai-day), plus .gitignore exclusions |

## 9. Cost Envelope (from spec)

- GKE Standard (~3×e2-standard-4): ~$0.30/hr
- Vertex AI Gemini Flash: ~$0.01–0.05/hr demo traffic
- Cloud DNS: negligible
- **Total:** ~$0.35–0.40/hr running
- Demo day: ~$3; 40hr rehearsal over 2 months: ~$15

Rule: tear down between rehearsals. Terraform rebuild is ~15 min.

## 10. Success Criteria

The demo is a success when:
1. The unguarded BurritBot answers an audience prompt injection attempt *and*
   the guarded BurritBot blocks the same attempt, both visible on the
   projector dashboard.
2. Every block is traceable: NeMo decision, LLM Guard scan result, or
   Kyverno/Falco event shows up as a span or log event in Grafana.
3. The audience sees the block count climb in real time on the side-by-side
   dashboard during Act 2.
4. If the live demo catches fire, the backup videos cover every segment and
   the talk still lands on time.
