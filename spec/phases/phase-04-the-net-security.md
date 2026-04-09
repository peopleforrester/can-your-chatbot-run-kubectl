# Phase 4: The Net — Security (Kyverno + Falco)

**Goal:** Admission-time and runtime security enforcement installed.
Kyverno policies reject unlabelled BurritBot pods and sidecars that do
not follow the `deinopis-*` naming convention. Falco rules tag
detections with `[deinopis, the-net, ...]` so Grafana can group them.

**Inputs:** Phase 3 complete. `security` namespace exists. `monitoring`
namespace has Prometheus ready to scrape Falco metrics.

**Outputs:**

- `security/kyverno/policies/require-deinopis-labels.yaml` —
  references `deinopis.io/layer`, `deinopis.io/model-source`, and
  `deinopis.io/model-hash`
- `security/kyverno/policies/require-deinopis-sidecar-naming.yaml` —
  references the `deinopis-` prefix
- `security/kyverno/policies/restrict-burritbot-network.yaml` —
  references `deinopis-net`
- `security/kyverno/tests/` — one subdirectory per policy with
  `kyverno-test.yaml` + pass/fail fixture pods
- `security/falco/rules/deinopis.yaml` — rules tagged with `deinopis`
  and `the-net`
- `gitops/apps/kyverno.yaml`, `gitops/apps/falco.yaml`

**Test Criteria (tests/test_phase_04_the_net_security.py):**

Static:

- `test_security_tree_exists`
- `test_kyverno_required_policies_exist` — three named policy files
- `test_kyverno_policies_are_valid_yaml_and_kind` — every policy is
  `ClusterPolicy` or `Policy` on `kyverno.io/*`
- `test_require_labels_policy_enforces_deinopis_labels`
- `test_sidecar_naming_policy_requires_deinopis_prefix`
- `test_network_policy_locks_guarded_burritbot_to_deinopis_net`
- `test_falco_rules_tagged_deinopis_the_net`

Live:

- `test_kyverno_admission_controller_running`
- `test_falco_daemonset_ready` — Falco DaemonSet pods all Ready
  (this is why Phase 1 forbids GKE Autopilot)

**Key Technology Decisions:**

- Kyverno 1.13+ with CEL expressions, not `pattern:` matches
- Falco 0.40+ with modern-bpf driver
- Policies use `validationFailureAction: Enforce`, not Audit — the
  demo depends on a visible rejection
- `restrict-burritbot-network` is a **generate** rule that creates a
  NetworkPolicy for `burritbot-guarded` (not a validate rule on Pods)

**Known Risk:** Kyverno 1.13 CEL syntax uses `object.metadata.labels['key']`
with bracket syntax; dot syntax silently no-ops on labels with slashes
like `deinopis.io/layer`.

**Completion Promise:** `<promise>PHASE4_DONE</promise>`

**Skill:** `.claude/skills/the-net-kyverno-deinopis.md`

**Commits:** 4 expected (Kyverno install; three policies with tests;
Falco install; Falco rules)
