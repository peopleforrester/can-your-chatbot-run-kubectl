# burritbot Phase $ARGUMENTS

You are building Phase $ARGUMENTS of the burritbot platform.

## Step 0 — Load context

Read in order:

1. `CLAUDE.md` — project-level rules (non-negotiable architecture decisions)
2. `PROJECT_STATE.md` — current status and resolved Phase 1 preconditions
3. `docs/BUILD-INSTRUCTIONS.md` — authoritative spec (verbatim from the
   burritbot plan)
4. `docs/PLAN.md` — phase-by-phase execution plan
5. `spec/phases/phase-0$ARGUMENTS-*.md` — phase spec (if present)
6. `.claude/skills/burritbot-architecture.md` — the ogre-faced spider metaphor
7. The skill file matching the component for this phase:
   - Phase 3 → `.claude/skills/the-eyes-otel-genai.md`
   - Phase 4 → `.claude/skills/the-net-kyverno-burritbot.md`
   - Phase 5 → `.claude/skills/the-net-ai-gateway.md`
   - Phase 6 → `.claude/skills/burritbot-vertex-ai.md`
   - Phase 7 → `.claude/skills/cast-net-toggle.md`

If the matching skill file is missing, **stop and write it first.**
Skills capture what the training data gets wrong.

## Step 1 — TDD red

Confirm the Phase $ARGUMENTS test file already expresses what "done"
looks like:

```bash
uv run pytest -q -m phase$ARGUMENTS -m static
```

Every static test for this phase should currently fail (red). If a
test is already passing, either it's vacuously passing on an empty
collection or the phase is partly done — check which before writing
any new code.

## Step 2 — TDD green (one component at a time)

For each component in this phase:

1. Read the matching skill file section for that component
2. Write the minimum file(s) that make the next red test go green
3. Re-run just the affected test:
   ```bash
   uv run pytest -q tests/test_phase_0${ARGUMENTS}_*.py::TEST_NAME
   ```
4. If green, move to the next test
5. If red, read the error — do not guess at fixes

## Step 3 — ABOUTME + type hints

Every file created must start with two ABOUTME lines. Every Python
function must have type annotations. Shell scripts must be executable
(`chmod +x`) and start with `#!/usr/bin/env bash` plus `set -euo pipefail`.

## Step 4 — Commit per component

After each component's tests go green, commit **that component only**:

```bash
git branch --show-current        # must be "staging"
git add <only-the-files-for-this-component>
git commit -m "Phase $ARGUMENTS: <component>: <what and why>"
```

Commit messages are technical. No "Claude", "AI", "LLM", or
"generated with" strings — the pre-commit hook will block those.

## Step 5 — Full suite + push

Before pushing:

```bash
uv run pytest -q                 # full suite, not just phase $ARGUMENTS
git push origin staging
```

## Step 6 — Merge to main

Per the global workflow (staging → main is autonomous, no
confirmation):

```bash
git checkout main && git merge --ff-only staging && git push origin main
git checkout staging
```

## Step 7 — Update PROJECT_STATE.md

Mark Phase $ARGUMENTS complete in the "What's Done" section and in the
in-flight task table. Commit and push that change on staging, then
fast-forward main.

## Rules that never change

- No mocks, stubs, or fallbacks. Tests hit real resources or they
  skip explicitly.
- No secrets committed. Use Secret Manager + External Secrets.
- `burritbot.io/*` labels are required on every BurritBot manifest.
- `burritbot-*` sidecar naming is required in `burritbot-net`.
- `cast-net.sh` is the live toggle name — never rename it.
