# Contributing

Create a focused branch from `main` using a `feature/`, `fix/`, `docs/`, or `chore/` prefix. Do not commit credentials, runtime databases, memory exports, private portraits, certificates, generated audio, or cache directories.

Production rollout must follow this path: push a branch, open a pull request, merge it into `main`, and let GitHub Actions deploy from the resulting trusted `main` commit. Do not deploy production changes from a direct local push to `main`.

Before publishing, confirm you are working in the real git checkout for `https://github.com/andre-ramos/live-ai-therapy.git`. If `/home/andre/codex/live-therapy` or another working directory is missing `.git` or points at the wrong remote, stop and locate the canonical checkout instead of cloning an ad hoc publish copy or continuing from a detached folder.

Before opening a pull request, run:

```bash
npm test
.venv/bin/python -m pytest backend/tests -q
.venv/bin/alembic heads
bash scripts/check-public-repo.sh
```

Pull requests should explain the user-visible behavior, privacy or migration impact, and verification performed. Keep database migrations forward-compatible with the previously deployed application because production rollback restores code but does not reverse an applied migration.

Code from public pull requests runs only on GitHub-hosted runners. The private MX deployment runner is restricted to trusted `main` commits produced by merging reviewed pull requests.
