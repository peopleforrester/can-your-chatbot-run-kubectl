# Phase 2: GitOps (The Web — bootstrap)

**Goal:** ArgoCD installed via Helm, an app-of-apps root Application
syncing, and the Deinopis namespaces created by ArgoCD rather than by
kubectl.

**Inputs:** Phase 1 complete. GKE cluster exists; kubeconfig is
current-context; `argocd` namespace exists.

**Outputs:**

- `gitops/bootstrap/app-of-apps.yaml` — root ArgoCD `Application` that
  points at `gitops/apps/`
- `gitops/argocd/values.yaml` — Helm values for the ArgoCD install
- `gitops/namespaces/namespaces.yaml` — multi-document YAML creating
  `argocd`, `monitoring`, `security`, `deinopis-net`,
  `burritbot-unguarded`, `burritbot-guarded`, `audience`
- `gitops/apps/` — directory of per-component Application manifests
  with `argocd.argoproj.io/sync-wave` annotations

**Test Criteria (tests/test_phase_02_gitops.py):**

Static:

- `test_gitops_tree_exists` — `gitops/bootstrap/`, `gitops/argocd/`,
  `gitops/namespaces/` all present
- `test_app_of_apps_manifest_valid` — valid `argoproj.io/*` Application
- `test_namespaces_manifest_includes_deinopis_net` — all seven
  namespaces declared
- `test_sync_wave_annotations_present` — at least one app under
  `gitops/apps/` carries `argocd.argoproj.io/sync-wave`

Live (skip without cluster):

- `test_argocd_server_running`
- `test_root_app_of_apps_synced` — root `Application` is Synced + Healthy

**Key Technology Decisions:**

- ArgoCD 3.x via upstream Helm chart
- App-of-apps pattern, not ApplicationSet (the scorecard is easier to
  reason about with explicit per-component Applications)
- Sync waves: `-10` namespaces, `-5` Kyverno, `0` monitoring and
  security, `1` ai-gateway + burritbot, `2` audience frontend
- The `deinopis-net` namespace has `pod-security.kubernetes.io/enforce:
  restricted` to force the guardrail sidecars to be explicit about
  capabilities

**Known Risk:** The `deinopis.io/layer: the-web` label on the ArgoCD
Application itself doesn't propagate to the deployed resources — that
labeling happens in Kyverno generate rules in Phase 4.

**Completion Promise:** `<promise>PHASE2_DONE</promise>`

**Skill:** none specific to Phase 2. ArgoCD patterns are well-covered
by the upstream docs.

**Commits:** 3 expected (ArgoCD Helm install; namespaces; app-of-apps root)
