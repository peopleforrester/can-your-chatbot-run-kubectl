# Burrito Bots to Guardrails — KubeCon NA 2026 Demo Platform

## What This Is
A GKE cluster running a complete AI guardrails demo stack for a KubeCon talk.
Two modes: UNGUARDED (chatbot with no protections) and GUARDED (full CNCF guardrails stack active).
The audience interacts with both via a web frontend and watches the difference on a Grafana dashboard in real-time.

Talk: **"Can Your Chatbot Run kubectl? Guardrails for LLMs on Kubernetes"** —
KubeCon NA 2026, Salt Lake City. Co-presenters: Michael Forrester, Whitney Lee.

## Repository Origin
Forked from kubeauto-idp (EKS). All AWS references must be converted to GCP equivalents.
The ArgoCD app-of-apps pattern, Kyverno policies, Falco rules, OTel collector, and Grafana dashboards
are carried forward. The AI-specific components (BurritBot, NeMo Guardrails, LLM Guard,
Envoy AI Gateway, GenAI OTel conventions) are new.

Reuse source repo lives **locally only** at
`~/repos/kubecon/2026_Kubecon_North_America_CNCF_Can_Your_Chatbot_Run_Kubectl/kubeauto-ai-day/`
and is excluded from this repo via `.gitignore`. See `docs/KUBEAUTO-REUSE-MAP.md`
for the per-file copy/adapt/extend/ignore map.

## How To Work
1. Read this file completely before writing any code.
2. Read `PROJECT_STATE.md` at session start to reconcile with actual repo state.
3. Read `docs/BUILD-INSTRUCTIONS.md` for the authoritative phase spec.
4. Read `docs/PLAN.md` for the execution plan and open decisions.
5. Work in phases. Complete each phase's tests before moving to the next.
6. Everything after Phase 2 is deployed as an ArgoCD Application. No kubectl apply.
7. No secrets in Git. Use GCP Secret Manager + External Secrets Operator.
8. Commit after each working component, not after each file.
9. When you hit a wall on GCP-specific config, search the docs. Do not guess IAM bindings.

## Architecture Decisions (non-negotiable)
- GKE Autopilot for the base cluster (simplifies GPU node provisioning)
  - **Likely override:** Phase 4 risk note recommends GKE Standard with node
    auto-provisioning so Falco DaemonSets work. Confirm this in Phase 1.
- Workload Identity Federation for all service accounts (no JSON key files)
- Vertex AI as the inference backend (not self-hosted model) for demo reliability
- ArgoCD app-of-apps with sync waves for deployment ordering
- Two namespaces for the chatbot: burritbot-unguarded and burritbot-guarded
- Single Grafana instance with split dashboards showing both versions side-by-side

## Phase Order
Phase 1: GKE Foundation (Terraform)
Phase 2: GitOps Bootstrap (ArgoCD)
Phase 3: Observability Stack (Prometheus, Grafana, OTel Collector with GenAI conventions)
Phase 4: Security Stack (Kyverno, Falco with AI-specific rules, SPIFFE/SPIRE)
Phase 5: AI Gateway Layer (Envoy AI Gateway or kgateway, NeMo Guardrails, LLM Guard)
Phase 6: BurritBot Application (unguarded + guarded versions)
Phase 7: Audience Interaction Frontend + Demo Runbook
Phase 8: Hardening + Backup Videos

## Critical Versions (pin these, do not use latest)
- GKE: 1.30+ (for DRA support)
- ArgoCD: 2.14+
- Kyverno: 1.13+ (CEL policies GA)
- Falco: 0.40+ (modern-bpf driver)
- OTel Collector: 0.100+ (GenAI semantic conventions support)
- OTel Weaver: 0.16+ (registry check, emit, live-check)
- spinybacked-orbweaver: latest (Whitney's auto-instrumentation agent)
- NeMo Guardrails: 0.11+
- LLM Guard: 0.3.17+
- Grafana: 11+

## Rules
- No kubectl apply after Phase 2 except for one-time ArgoCD bootstrap
- No GCP service account JSON keys. Workload Identity Federation only.
- No hardcoded project IDs. Use variables.
- Every Helm chart gets a values.yaml in gitops/apps/<component>/
- Test before commit. If tests fail, do not commit.
- All Kyverno policies must be in Audit mode first, then Enforce after validation.
- Falco rules must have explicit priority levels and tags.
- OTel collector config must include the GenAI semantic convention processors.

## TDD Protocol (5-step cycle, carried over from kubeauto-idp)
1. Write a failing test for the specific component/behavior.
2. Run it to confirm it fails (expected failure, not import error).
3. Write the minimal code to make it pass.
4. Run it to confirm it passes.
5. Refactor if needed, re-run to confirm still green.

Skipping step 2 means the test may be vacuously passing and proves nothing.

## ABOUTME Comments
All code files (Python, Shell, YAML with logic, Terraform, Dockerfiles) start with a
brief 2-line comment, each line starting with `ABOUTME:`. Pure-docs markdown is exempt.

## No Mocks, Stubs, or Fallbacks
All tests hit real infrastructure. No mocked Kubernetes clients, no stubbed GCP
calls, no fake HTTP servers. Tests require a running cluster. If the cluster isn't
available, the test fails — that's correct behavior. Code must fail explicitly
rather than silently fall back to defaults.

## Git Workflow (staging → main)
- Work on `staging` branch. Main is protected.
- Commit after each working component. Test before commit; if tests fail, do not commit.
- After each phase: commit staging, push staging, merge to main, push main (autonomous).
- Commit messages are professional and technical. No AI/Claude references.

## Session Discipline
- Read PROJECT_STATE.md first every session.
- Update PROJECT_STATE.md at every transition (plan approval, phase completion, pre-commit).
- Run each phase as a separate Claude Code session to avoid context window overflow.
- The exact per-phase session commands are in `docs/BUILD-INSTRUCTIONS.md` §
  "Claude Code Execution Strategy".
