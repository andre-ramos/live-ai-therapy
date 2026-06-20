#!/usr/bin/env bash
set -euo pipefail

forbidden_paths='(^|/)(\.env($|\.)|data/|certs/|__pycache__/|\.pytest_cache/|\.mypy_cache/|\.ruff_cache/|\.venv/|node_modules/|site/)|(^|/)Sandy\.jpeg$|\.local\.md$|\.(db|sqlite|sqlite3|pem|key|p12|pfx|log)$'
tracked="$(git ls-files)"
violations="$(printf '%s\n' "$tracked" | grep -Ei "$forbidden_paths" | grep -Ev '^\.env\.example$' || true)"
if [[ -n $violations ]]; then
  printf 'Forbidden private or generated files are tracked:\n%s\n' "$violations" >&2
  exit 1
fi

if git grep -IEn '/home/andre|192\.168\.0\.12' -- ':!scripts/check-public-repo.sh'; then
  printf 'Personal deployment data was found.\n' >&2
  exit 1
fi

if git grep -IEn '^(OPENAI_API_KEY|ELEVENLABS_API_KEY|ELEVENLABS_VOICE_ID)=.+' -- ':!install.sh'; then
  printf 'A populated provider credential assignment was found.\n' >&2
  exit 1
fi

printf 'Public repository privacy checks passed.\n'
