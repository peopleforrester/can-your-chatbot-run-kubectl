# Project State — Deinopis (Can Your Chatbot Run kubectl?)

## Current Status
**Phases 1–8 offline build complete. All static tests green.**
Every phase has been authored offline and committed on the autonomous
staging→main workflow. Live validation (terraform apply, Helm installs,
live Kyverno + Falco + Envoy smoke tests) is deferred to a session with
GCP auth and cluster access. Nothing in this repo has touched a live
cluster yet.

## Talk Context
- Talk: "Can Your Chatbot Run kubectl? Guardrails for LLMs on Kubernetes"
- Venue: KubeCon NA 2026, Salt Lake City
- Speakers: Whitney Lee and Michael Forrester
- Format: Two-act live demo (unguarded then guarded BurritBot on GKE)
- Platform name: **Deinopis** (ogre-faced spider — The Eyes + The Net)
- Chatbot name: **BurritBot** (Chipotle viral chatbot incident as narrative hook)

## What's Done

### Phase 0 — Bootstrap
- [x] Git repo initialized (`main` + `staging` branches pushed to origin)
- [x] GitHub repo: `peopleforrester/can-your-chatbot-run-kubectl`
- [x] `kubeauto-ai-day/` subdir kept local-only (gitignored)
- [x] `CLAUDE.md`, `README.md`, `.gitignore`
- [x] `docs/BUILD-INSTRUCTIONS.md` (verbatim spec + preamble)
- [x] `docs/PLAN.md`, `docs/KUBEAUTO-REUSE-MAP.md`
- [x] `PROJECT_STATE.md` (this file)

### Offline Build (Tasks #7 – #18)
| # | Task | Status | Commit |
|---|------|--------|--------|
| 7 | Rebaseline docs to Deinopis spec | completed | 5daad64 |
| 8 | Python env + test scaffolding | completed | 1608114 |
| 9 | Project skills and slash commands | completed | c978e63 |
| 10 | Phase specs + scorecard skeleton | completed | 500bef7 |
| 11 | Phase 1: Terraform (GKE Standard + NAP) | completed | c89a4b5 |
| 12 | Phase 2: ArgoCD GitOps bootstrap | completed | 25d7f5d |
| 13 | Phase 3: The Eyes (observability) | completed | af6629a |
| 14 | Phase 4: The Net — Security (Kyverno + Falco) | completed | 1d77e42 |
| 15 | Phase 5: The Net — AI Gateway | completed | e4602e2 |
| 16 | Phase 6: BurritBot application (gemini-3-pro) | completed | cdb1dda |
| 17 | Phase 7: Audience frontend + rate limiter | completed | 542c194 |
| 18 | Phase 8: Hardening, runbook, docs | completed | (this commit) |

### Static Test Totals
- Phase 1: 8 passed
- Phase 2: 4 passed
- Phase 3: 6 passed
- Phase 4: 7 passed
- Phase 5: 6 passed
- Phase 6: 7 passed
- Phase 7: 7 passed
- Phase 8: 5 passed
- **Total: 50 static tests green. Live tests skip cleanly when kubeconfig
  is absent — no mocks, no fallbacks.**

## Phase 1 Preconditions (authoritative)
1. **GCP project ID:** `deinopis-kubecon-2026` (placeholder — confirm real
   ID before `terraform apply`).
2. **Region:** `us-west1`.
3. **GKE mode:** **Standard with node auto-provisioning.** Not Autopilot —
   Falco DaemonSet needs privileged container support.
4. **Gemini model:** `gemini-3-pro` (GA) accessed via `google-genai` with
   `vertexai=True`. 1.5 is unsupported; 2.0 Flash is retired; 2.5 Flash/Pro
   retire 2026-10-16 — four weeks before the talk; 3 Flash is preview-tier.
   3 Pro is the only Vertex AI model guaranteed to be live on demo day.
5. **Audience frontend backend:** FastAPI (matches the rest of the stack).
6. **Licensing:** Apache 2.0 (matching kubeauto-ai-day lineage).

## Local Tooling (as of 2026-04-09)
- ✅ Installed: `yamllint`, `jq`, `kyverno`, `shellcheck`, `uv`, `python3.13`
- ❌ Missing: `terraform`, `kubectl`, `kubeconform`, `helm`, `docker`

Offline TDD strategy: Python code via pytest; Kyverno via `kyverno test`;
YAML via yamllint; JSON dashboards via `jq empty`; shell via shellcheck;
Terraform `validate` deferred to a session with Terraform installed.

## Next Session — Phase 1 Live Validation
Once a GCP project is confirmed and Terraform is installed:

```bash
claude -p "Read CLAUDE.md, PROJECT_STATE.md, docs/BUILD-INSTRUCTIONS.md, \
and docs/PLAN.md. Validate Phase 1: GKE Foundation. Run terraform validate, \
terraform plan, then terraform apply. Run tests/test_phase_01_foundation.py \
with the live marker." --max-iterations 20
```

Then walk Phases 2 → 8 forward in the same autonomous staging→main
workflow, promoting YELLOW scorecard rows to GREEN as each live check
passes. **Do not green-wash the scorecard.**

## Demo-Day Artifacts (Phase 8)
- `docs/RUNBOOK.md` — Pre-flight / Act 1 / Cast the Net / Act 2 / Teardown / Rollback
- `docs/SCORECARD.md` — honest per-component status, YELLOW where live
  validation has not happened yet
- `scripts/teardown.sh` — `terraform destroy` with a two-step confirmation
- `scripts/cast-net.sh` — the single-command live traffic toggle

## Branch & Test Status
- **Branch**: `staging` (default working branch)
- **Remote**: `origin → https://github.com/peopleforrester/can-your-chatbot-run-kubectl`
- **Static tests**: 50 passing, 0 failing, live tests skip when kubeconfig absent

## Key References
- `CLAUDE.md` — project Claude Code instructions
- `docs/BUILD-INSTRUCTIONS.md` — authoritative Deinopis spec
- `docs/RUNBOOK.md` — demo-day operational runbook
- `docs/SCORECARD.md` — per-component scorecard
- `spec/BUILD-SPEC.md` — build-time pointer and completion protocol
- `spec/phases/phase-0[1-8]-*.md` — per-phase specs with completion promises
- Local reuse source: `~/repos/kubecon/.../kubeauto-ai-day/` (local-only)
- Remote reuse source: https://github.com/peopleforrester/kubeauto-ai-day
