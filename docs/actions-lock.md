# GitHub Actions dependency updates

GitHub Actions dependencies are recorded in `.github/workflows/actions.lock`.
This repository applies the shared `github>gkzz/renovate-config:actions-lock`
preset. Confirm that the first Renovate action update also updates the lockfile
before merging it.
Review both the workflow changes and the resolved commits before merging.

For setup, manual updates, and verification, follow the
[shared guide](https://github.com/gkzz/renovate-config/blob/main/docs/actions-lock.md).

Local composite actions currently contain no remote action dependencies and use
`./` references. Before adding remote dependencies inside a local action, follow
the local action instructions linked from the shared guide.

The verification workflow checks coverage and dependencies on pull requests,
pushes to `main`, and manual dispatches.
