# Claude Code Configuration — burritbot

This directory holds the project-specific Claude Code customisation:
skills (read before generating config), commands (slash commands that
orchestrate multi-step workflows), and hooks.

## Skills (`skills/`)

Skills are reference files Claude reads *before* touching a component.
They capture what the training data gets wrong — version pins, wrong
API group names, misleading examples from tutorials.

| Skill | When to read |
|-------|--------------|
| `burritbot-architecture.md` | Always, before starting work in a new session |
| `the-eyes-otel-genai.md` | Before editing anything under `observability/` |
| `the-net-kyverno-burritbot.md` | Before editing `security/kyverno/` |
| `the-net-ai-gateway.md` | Before editing `ai-gateway/` |
| `burritbot-vertex-ai.md` | Before editing `apps/burritbot/` |
| `cast-net-toggle.md` | Before editing `scripts/cast-net.sh` |

## Commands (`commands/`)

| Command | What it does |
|---------|--------------|
| `/burritbot-phase N` | TDD build loop for Phase N (red → green → commit per component) |
| `/burritbot-validate N|all` | Run static + optional live tests for Phase N or all phases |
| `/burritbot-cast-net cast|recall|status|rehearse` | Live traffic toggle between guarded and unguarded paths |

## Hooks

Hooks live at the repo root (pre-commit) and in `~/.claude/` (session
start / stop). The project does not yet ship its own Claude Code hooks
— the global `commit-msg-validate` hook is sufficient for now.

## Rule of thumb

When in doubt: read `burritbot-architecture.md` first, then the layer
skill, then the BUILD-INSTRUCTIONS spec, then write code. The order
matters — the skills encode decisions that already have tests behind
them.
