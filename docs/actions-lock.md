# GitHub Actions dependency updates

GitHub Actions dependencies are recorded in `.github/workflows/actions.lock`.
Renovate updates action versions and regenerates the lockfile in the same PR,
using the shared `github>gkzz/renovate-config:actions-lock` preset.
Review both the workflow changes and the resolved commits before merging.

For manual workflow changes, install the same extension version as
`.github/workflows/verify-lockfile.yml`, then regenerate and verify the lockfile:

```sh
gh extension install github/gh-actions-lock --pin v0.4.1
gh actions-lock --no-narrow --ignore-local-actions
gh actions-lock --verify
```

Commit the workflow changes and lockfile together. New workflows must be onboarded
with the generation command above; Renovate does not onboard them automatically.
Local composite actions currently contain no remote action dependencies and retain
`./` references. If remote dependencies are added inside a local action, migrate
its callers with `gh actions-lock --migrate-local-actions --no-narrow` so those
transitive dependencies are locked as well.

The verification workflow checks coverage and dependencies on pull requests,
pushes to `main`, and manual dispatches. For an offline coverage check, use
`gh actions-lock --verify-local`; it does not replace the online verification.
