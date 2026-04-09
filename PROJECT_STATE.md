# Project State — Deinopis (Can Your Chatbot Run kubectl?)

## Current Status
**Phase 0 — Bootstrap complete. Offline build of Phases 1-8 in progress.**
Spec captured, plan drafted, reuse map scoped. No live infrastructure yet —
all Phase 1-8 artifacts are being authored offline (Terraform, manifests,
policies, tests, app code). Live validation deferred to sessions with GCP
auth + cluster access.

## Talk Context
- Talk: "Can Your Chatbot Run kubectl? Guardrails for LLMs on Kubernetes"
- Venue: KubeCon NA 2026, Salt Lake City
- Speakers: Whitney Lee and Michael Forrester
- Format: Two-act live demo (unguarded then guarded BurritBot on GKE)
- Platform name: **Deinopis** (ogre-faced spider — The Eyes + The Net)
- Chatbot name: **BurritBot** (kept friendly; narrative hook is the
  Chipotle viral chatbot incident)

## What's Done (Phase 0)
- [x] Git repo initialized (`main` + `staging` branches pushed to origin)
- [x] GitHub repo: `peopleforrester/can-your-chatbot-run-kubectl` (public)
- [x] `kubeauto-ai-day/` subdir is local-only reference (excluded via .gitignore)
- [x] `CLAUDE.md` — Deinopis-branded project instructions at repo root
- [x] `README.md` — Deinopis / ogre-faced-spider description with talk context
- [x] `.gitignore` — excludes kubeauto-ai-day, secrets, Terraform state, Python noise
- [x] `docs/BUILD-INSTRUCTIONS.md` — authoritative Deinopis spec, preserved verbatim
  (with preamble noting speaker-ordering and `gemini-1.5-flash → gemini-2.5-flash`
  deviations)
- [x] `docs/PLAN.md` — execution plan with phase strategy, reuse approach,
  resolved Phase 1 preconditions
- [x] `docs/KUBEAUTO-REUSE-MAP.md` — per-file copy/adapt/extend/ignore map,
  updated for `deinopis-net` namespace and `deinopis.io/*` labels
- [x] `PROJECT_STATE.md` — this file

## Phase 1 Preconditions — RESOLVED (placeholders pending Michael's confirmation)
These are authoritative defaults for offline authoring. Confirm or override
before running `terraform apply`.

1. **GCP project ID:** `deinopis-kubecon-2026` (placeholder — confirm real ID
   before Phase 1 `terraform apply`).
2. **Region:** `us-west1` (close to SLC; confirm Vertex AI + Gemini 2.5 Flash
   availability at build time).
3. **GKE mode:** **Standard with node auto-provisioning.** Not Autopilot —
   Falco DaemonSets need privileged container support.
4. **Gemini model:** `gemini-2.5-flash` (GA). Researched 2026-04-09:
   1.5 Flash is unsupported; 2.0 Flash shuts down 2026-06-01 (before the
   talk); 3 Flash is preview-tier. 2.5 Flash is the chosen default.
5. **Audience frontend backend:** **FastAPI** (Python, matches the rest of
   the stack).
6. **Licensing:** Apache 2.0 (matching kubeauto-ai-day lineage).

## Local Tooling (as of 2026-04-09)
- ✅ Installed: `yamllint`, `jq`, `kyverno`, `shellcheck`, `uv`, `python3.13`
- ❌ Missing: `terraform`, `kubectl`, `kubeconform`, `helm`, `docker`

**TDD strategy given missing tooling:**
- **Python code** (FastAPI backend, BurritBot, test helpers): true pytest TDD
- **Kyverno policies**: `kyverno test` — true TDD with policy unit tests
- **YAML files** (Helm values, Application manifests, policies): `yamllint`
  syntactic + structural checks
- **JSON dashboards**: `jq empty` validity checks
- **Shell scripts** (`cast-net.sh`, teardown): `shellcheck`
- **Terraform**: `terraform validate` / `terraform plan` deferred to Michael's
  box or a future session with terraform installed. Phase 1 commits HCL
  authored to spec but not locally validated.

## What's In Flight (offline authoring, current session)
All 13 tasks from the in-flight task list. Working order (lowest ID first):

| # | Task | Status |
|---|------|--------|
| 7 | Rebaseline all docs to Deinopis spec | **in_progress** |
| 8 | Python env + test scaffolding | pending |
| 9 | Claude Code skills and commands | pending |
| 10 | Phase specs (spec/phases/*.md) | pending |
| 11 | Phase 1: Terraform (GKE Standard + NAP) | pending |
| 12 | Phase 2: ArgoCD GitOps bootstrap | pending |
| 13 | Phase 3: The Eyes (observability) | pending |
| 14 | Phase 4: The Net — Security (Kyverno + Falco) | pending |
| 15 | Phase 5: The Net — AI Gateway | pending |
| 16 | Phase 6: BurritBot application (gemini-2.5-flash) | pending |
| 17 | Phase 7: Audience frontend + FastAPI rate limiter | pending |
| 18 | Phase 8: Hardening, runbook, docs | pending |
| 19 | Final PROJECT_STATE update + staging→main merge | pending |

## Next Session Command (Phase 1 live validation, when cluster is ready)
```bash
claude -p "Read CLAUDE.md, PROJECT_STATE.md, docs/BUILD-INSTRUCTIONS.md, \
and docs/PLAN.md. Validate Phase 1: GKE Foundation. Run terraform validate, \
terraform plan, then terraform apply. Run tests/test_phase_01_foundation.py." \
  --max-iterations 20
```

## Branch & Test Status
- **Branch**: `staging` (default working branch)
- **Tests**: none yet — Task #8 writes the first scaffolding and per-phase stubs
- **Remote**: `origin → https://github.com/peopleforrester/can-your-chatbot-run-kubectl`

## Key References
- `CLAUDE.md` — project Claude Code instructions
- `docs/BUILD-INSTRUCTIONS.md` — authoritative Deinopis spec (verbatim + preamble)
- `docs/PLAN.md` — execution plan
- `docs/KUBEAUTO-REUSE-MAP.md` — reuse inventory
- Local reuse source: `~/repos/kubecon/2026_Kubecon_North_America_CNCF_Can_Your_Chatbot_Run_Kubectl/kubeauto-ai-day/` (not committed)
- Remote reuse source: https://github.com/peopleforrester/kubeauto-ai-day
