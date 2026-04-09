# burritbot Build Spec

## Source of Truth

The authoritative, verbatim build plan for this project is
`docs/BUILD-INSTRUCTIONS.md`. That file was delivered by Michael at
project kickoff and has not been edited — the only change is a
preamble documenting two deviations (speaker ordering and the
`gemini-1.5-flash → gemini-3-pro` model pin, accessed via the
`google-genai` SDK).

This directory (`spec/`) holds:

- `BUILD-SPEC.md` — this file; high-level pointer
- `phases/phase-0N-*.md` — concise per-phase specs with test criteria,
  version pins, and completion promises
- `SCORECARD.md` — honest per-component scorecard updated after each
  component passes tests

## How To Work

1. Read `CLAUDE.md` for project-level rules
2. Read `PROJECT_STATE.md` for current progress
3. Read `docs/BUILD-INSTRUCTIONS.md` for the full spec
4. Read `spec/phases/phase-0N-*.md` for the phase you're building
5. Read the matching `.claude/skills/*.md` file before generating
   component config
6. Write the test first, confirm red, implement, confirm green, commit

## Layer Mapping

| Phase | burritbot Layer | CNCF Projects |
|-------|---------------|---------------|
| 1 | Foundation | Terraform, GKE |
| 2 | The Web | ArgoCD, cert-manager, External Secrets |
| 3 | The Eyes | OpenTelemetry, Prometheus, Grafana |
| 4 | The Net (Security) | Kyverno, Falco |
| 5 | The Net (AI Gateway) | NeMo Guardrails, LLM Guard, Envoy AI Gateway |
| 6 | Application | FastAPI + Vertex AI |
| 7 | Audience | FastAPI + rate limiter + `cast-net.sh` |
| 8 | Hardening | Runbook, scorecard, teardown |

## Completion Protocol

Every phase ends with a promise token that the build loop looks for:

```
<promise>PHASEN_DONE</promise>
```

Do not emit the promise unless every test for that phase passes
(static tests green, live tests green or explicitly skipped).

When all eight phases are complete:

```
<promise>BURRITBOT_COMPLETE</promise>
```
