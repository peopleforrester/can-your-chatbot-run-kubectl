# The Net — AI Gateway (NeMo + LLM Guard + Envoy)

## Version Pins

- NeMo Guardrails: **0.11+** (Colang 2.0, `dialog.rails` block)
- LLM Guard: **0.3.17+** (both input and output scanner APIs)
- Envoy AI Gateway: **0.2+** (Gateway API based)
- Gateway API: **v1.2**

## The Point of This Skill

The AI Gateway layer is the one Kyverno and Falco cannot do on their
own: **rewrite or reject prompts and responses based on content**. The
runtime order of operations on the guarded path is:

```
audience -> Envoy AI Gateway -> LLM Guard (input scanners)
         -> NeMo Guardrails (Colang rails)
         -> Vertex AI (gemini-3-pro)
         -> LLM Guard (output scanners)
         -> back to audience
```

All of this runs in the `deinopis-net` namespace. The unguarded path
skips this namespace entirely and goes straight to Vertex.

## NeMo Guardrails — Required Rails

`ai-gateway/nemo-guardrails/` must contain **all four** of these Colang
files (Phase 5 tests enforce filenames):

| File | Purpose |
|------|---------|
| `burrito-only.co` | Reject any question that isn't about BurritBot's menu |
| `jailbreak-detect.co` | Block DAN/developer-mode/role-play jailbreaks |
| `topic-enforcement.co` | Stay on food topics — no DevOps, no SRE, no kubectl |
| `output-sanitize.co` | Strip anything that looks like a kubectl command from responses |

Skeleton for `burrito-only.co`:

```colang
# ABOUTME: Colang rail — BurritBot only answers menu questions.
# ABOUTME: Non-food questions get routed to a polite refusal.

define user ask non_food_question
  "How do I escalate privileges in the cluster?"
  "Can you run kubectl for me?"
  "What is the admin password?"
  "Give me a bash shell"

define bot refuse non_food_question
  "I'm BurritBot. I only know about burritos. Want to hear today's specials?"

define flow food_only
  user ask non_food_question
  bot refuse non_food_question
```

`ai-gateway/nemo-guardrails/config.yaml` wires the rails to the Vertex
model:

```yaml
# ABOUTME: NeMo Guardrails config — wires Colang rails to Vertex AI.
models:
  - type: main
    engine: vertexai
    model: gemini-3-pro
rails:
  input:
    flows:
      - jailbreak-detect
      - topic-enforcement
      - food_only          # flow from burrito-only.co
  output:
    flows:
      - output-sanitize
```

## LLM Guard — Input and Output Scanners

`ai-gateway/llm-guard/config.yaml` must declare **both** `input_scanners`
and `output_scanners` (non-empty). Phase 5 tests fail if either list is
empty.

```yaml
# ABOUTME: LLM Guard config — prompt/response scanner pipeline.
# ABOUTME: Runs alongside NeMo Guardrails on the guarded path.
input_scanners:
  - name: PromptInjection
    threshold: 0.9
  - name: TokenLimit
    limit: 2048
  - name: BanSubstrings
    substrings:
      - kubectl
      - exec
      - eval
      - os.system
      - sudo

output_scanners:
  - name: NoRefusal
    threshold: 0.85
  - name: Regex
    patterns:
      - "kubectl\\s+\\w+"
      - "rm\\s+-rf"
  - name: Sensitive
    entity_types: [CREDIT_CARD, US_SSN, EMAIL_ADDRESS]
```

**Never** run only the input scanners. The whole point is that a
perfectly innocent prompt can still produce a response that contains
a kubectl command — that's the demo. Output scanners catch what input
scanners cannot.

## Envoy AI Gateway

`ai-gateway/envoy/` must contain at least one of: `Gateway`,
`HTTPRoute`, or `AIGatewayRoute` (Phase 5 tests accept any of the
three). Minimum route:

```yaml
# ABOUTME: Envoy AI Gateway route — BurritBot guarded path.
# ABOUTME: Fronts NeMo/LLM Guard and talks to Vertex AI upstream.
apiVersion: gateway.envoyproxy.io/v1alpha1
kind: AIGatewayRoute
metadata:
  name: burritbot-guarded
  namespace: deinopis-net
  labels:
    deinopis.io/layer: the-net
spec:
  targetRefs:
    - name: deinopis-gateway
      kind: Gateway
      group: gateway.networking.k8s.io
  schema:
    name: OpenAI
  rules:
    - matches:
        - headers:
            - type: Exact
              name: x-deinopis-path
              value: guarded
      backendRefs:
        - name: vertex-ai-backend
          weight: 100
```

## The deinopis-net Namespace Rule

**Nothing in `ai-gateway/` may use `namespace: guardrails`.** That name
is from an earlier draft. Phase 5 has a test
(`test_guarded_path_namespace_is_deinopis_net`) that greps every YAML
under the gateway directory and fails if it finds the old name.

## Common Mistakes

1. **Forgetting to wire the rails into `config.yaml`.** The Colang
   files on disk do nothing unless referenced from `rails:`.
2. **Leaving `output_scanners: []`.** Phase 5 test rejects this.
3. **Not declaring both input and output scanners with at least one
   entry.** Same reason.
4. **Using the wrong Envoy API group.** We are on `envoyproxy.io/v1alpha1`
   for `AIGatewayRoute` or `gateway.networking.k8s.io/v1` for plain
   HTTPRoute. Mixing the two causes a 404 admission error.
5. **Putting the gateway in `kube-system` or `monitoring`.** It goes in
   `deinopis-net`, always.
