# The Net — Kyverno Policies (Deinopis Flavour)

## Version Pins

- Kyverno: **1.13+** (CEL expressions, validate.cel blocks, policy exceptions)
- Kyverno Helm chart: **3.3.x** or later
- `kyverno test` CLI version must match the cluster version

## The Point of This Skill

The Net's admission-time enforcement happens here. Three policies are
load-bearing for the demo; every other Kyverno policy is bonus:

1. `require-deinopis-labels` — every Pod in the BurritBot namespaces
   must carry `deinopis.io/layer`, `deinopis.io/model-source`,
   `deinopis.io/model-hash`. Unlabelled workloads get rejected.
2. `require-deinopis-sidecar-naming` — any sidecar container must have a
   name starting with `deinopis-`. This is how you know at a glance
   whether a pod has The Net applied.
3. `restrict-burritbot-network` — the guarded BurritBot namespace can
   only talk to `deinopis-net`. No direct egress to Vertex AI, no
   shortcut around the gateway.

Phase 4 tests fail until these three policies exist with these exact
filenames under `security/kyverno/policies/`.

## Policy Skeleton — require-deinopis-labels

```yaml
# ABOUTME: Kyverno policy — require deinopis.io labels on BurritBot pods.
# ABOUTME: Rejects admission if layer / model-source / model-hash are missing.
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-deinopis-labels
  annotations:
    policies.kyverno.io/title: Require deinopis.io labels
    policies.kyverno.io/category: deinopis
    deinopis.io/layer: the-net
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: require-labels
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaces:
                - burritbot-unguarded
                - burritbot-guarded
                - deinopis-net
      validate:
        message: >-
          Pods in BurritBot namespaces must carry
          deinopis.io/layer, deinopis.io/model-source, and
          deinopis.io/model-hash labels.
        cel:
          expressions:
            - expression: >
                has(object.metadata.labels) &&
                has(object.metadata.labels['deinopis.io/layer']) &&
                has(object.metadata.labels['deinopis.io/model-source']) &&
                has(object.metadata.labels['deinopis.io/model-hash'])
```

The CEL check — *not* a `pattern:` match — is what we want from
Kyverno 1.13. It's faster, and it gives a better audience demo when
you `kubectl apply` a pod without the labels.

## Policy Skeleton — require-deinopis-sidecar-naming

```yaml
# ABOUTME: Kyverno policy — sidecar containers must be named deinopis-*.
# ABOUTME: Makes The Net visible via container naming on every pod.
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-deinopis-sidecar-naming
  annotations:
    deinopis.io/layer: the-net
spec:
  validationFailureAction: Enforce
  rules:
    - name: sidecars-must-be-deinopis-prefixed
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaces: [deinopis-net]
      validate:
        message: >-
          Every container in deinopis-net after index 0 must be named
          with the deinopis- prefix.
        cel:
          expressions:
            - expression: >
                object.spec.containers.all(c,
                  c == object.spec.containers[0] ||
                  c.name.startsWith('deinopis-'))
```

## Policy Skeleton — restrict-burritbot-network

This one is a generator that creates a matching NetworkPolicy rather
than a validation rule — the audience sees the restriction on the
`burritbot-guarded` namespace immediately:

```yaml
# ABOUTME: Kyverno policy — generate NetworkPolicy limiting guarded BurritBot.
# ABOUTME: The guarded namespace may only talk to deinopis-net.
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-burritbot-network
  annotations:
    deinopis.io/layer: the-net
spec:
  generateExisting: true
  rules:
    - name: generate-netpol
      match:
        any:
          - resources:
              kinds: [Namespace]
              names: [burritbot-guarded]
      generate:
        apiVersion: networking.k8s.io/v1
        kind: NetworkPolicy
        name: burritbot-guarded-egress-deinopis-net
        namespace: burritbot-guarded
        data:
          spec:
            podSelector: {}
            policyTypes: [Egress]
            egress:
              - to:
                  - namespaceSelector:
                      matchLabels:
                        kubernetes.io/metadata.name: deinopis-net
```

## Kyverno Tests (true TDD)

Write `kyverno test` cases in `security/kyverno/tests/` **before** the
policy. Layout:

```
security/kyverno/tests/
  require-deinopis-labels/
    kyverno-test.yaml       # test manifest
    good-pod.yaml           # should PASS (has all labels)
    missing-label-pod.yaml  # should FAIL
```

Then: `kyverno test security/kyverno/tests/` must return 0 before the
commit.

## Common Mistakes

1. **Validating in the kube-system or kyverno namespaces.** Always
   scope to the BurritBot or `deinopis-net` namespaces. The demo never
   touches system namespaces.
2. **Using `pattern:` when `cel:` works.** The `cel:` block produces
   a cleaner rejection message and is what 1.13+ expects.
3. **Forgetting `validationFailureAction: Enforce`.** Audit mode means
   the policy fires in logs but lets the pod in — which kills the demo
   punch line.
4. **Missing the `deinopis.io/layer: the-net` annotation on the policy
   itself.** The scorecard groups policies by layer via this
   annotation.
