# Contributing

Create a focused branch from `main` using a `feature/`, `fix/`, `docs/`, or `chore/` prefix. Do not commit credentials, runtime databases, memory exports, private portraits, certificates, generated audio, or cache directories.

Before opening a pull request, run:

```bash
npm test
.venv/bin/python -m pytest backend/tests -q
.venv/bin/alembic heads
bash scripts/check-public-repo.sh
```

Pull requests should explain the user-visible behavior, privacy or migration impact, and verification performed. Keep database migrations forward-compatible with the previously deployed application because production rollback restores code but does not reverse an applied migration.

Code from public pull requests runs only on GitHub-hosted runners. The private MX deployment runner is restricted to trusted `main` commits.
