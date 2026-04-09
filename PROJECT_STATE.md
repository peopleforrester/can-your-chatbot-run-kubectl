# Project State — Can Your Chatbot Run kubectl?

## Current Status
**Phase 0 — Bootstrap (repo initialization).**
Spec captured, plan drafted, reuse map scoped. No infrastructure built yet.

## Talk Context
- Talk: "Can Your Chatbot Run kubectl? Guardrails for LLMs on Kubernetes"
- Venue: KubeCon NA 2026, Salt Lake City
- Speakers: Whitney Lee, Michael Forrester
- Format: Two-act live demo (unguarded then guarded BurritBot on GKE)

## What's Done (Phase 0)
- [x] Git repo initialized locally (`main` branch, no commits yet at time of writing)
- [x] Decision: repo name = `peopleforrester/can-your-chatbot-run-kubectl`, public
- [x] Decision: `kubeauto-ai-day/` subdir is local-only reference (excluded via .gitignore)
- [x] `CLAUDE.md` — project instructions at repo root
- [x] `README.md` — repo description and talk context
- [x] `.gitignore` — excludes kubeauto-ai-day, secrets, Terraform state, Python noise
- [x] `docs/BUILD-INSTRUCTIONS.md` — authoritative spec, preserved verbatim
- [x] `docs/PLAN.md` — execution plan with phase strategy, reuse approach, open decisions
- [x] `docs/KUBEAUTO-REUSE-MAP.md` — per-file copy/adapt/extend/ignore map
- [x] `PROJECT_STATE.md` — this file

## What's Next (Phase 1 preconditions)
Before a Phase 1 session kicks off, Michael needs to decide on:
1. **GCP project ID.** Spec suggests `burritbot-kubecon-2026`. Confirm it exists or
   create it; note the actual ID in `infrastructure/terraform/terraform.tfvars`.
2. **Region.** Spec suggests `us-west1` (close to SLC). Confirm Vertex AI + GKE
   availability for the chosen Gemini model.
3. **GKE Autopilot vs Standard.** Spec defaults to Autopilot, but Phase 4 risk note
   recommends Standard with node auto-provisioning so Falco DaemonSets work.
   Likely answer: **Standard with NAP** — confirm before writing Terraform.
4. **Billing + quota.** GKE Standard + Vertex AI Gemini calls need a billing
   account and baseline quotas.

## Next Session Command (Phase 1)
```bash
claude -p "Read CLAUDE.md, PROJECT_STATE.md, docs/BUILD-INSTRUCTIONS.md, \
and docs/PLAN.md. Execute Phase 1: GKE Foundation. Write tests first, \
then implement until all tests pass." --max-iterations 20
```

## Branch & Test Status
- **Branch**: `staging` (set as default working branch going forward)
- **Tests**: none yet — Phase 1 writes the first `tests/test_phase_01_foundation.py`
- **Remote**: `origin → https://github.com/peopleforrester/can-your-chatbot-run-kubectl` (created during Phase 0)

## Key References
- `CLAUDE.md` — project Claude Code instructions
- `docs/BUILD-INSTRUCTIONS.md` — authoritative spec (verbatim)
- `docs/PLAN.md` — execution plan
- `docs/KUBEAUTO-REUSE-MAP.md` — reuse inventory
- Local reuse source: `~/repos/kubecon/2026_Kubecon_North_America_CNCF_Can_Your_Chatbot_Run_Kubectl/kubeauto-ai-day/` (not committed)
- Remote reuse source: https://github.com/peopleforrester/kubeauto-ai-day
