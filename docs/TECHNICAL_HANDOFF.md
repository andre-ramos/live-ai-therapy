# Technical Handoff

## Runtime architecture

FastAPI serves the dependency-free HTML/CSS/ES-module frontend and JSON/multipart APIs. Uvicorn listens on loopback, while Caddy terminates internal TLS. SQLAlchemy stores sessions, messages, summaries, structured continuity, and memory metadata in SQLite. ChromaDB stores same-language semantic vectors.

`backend/app/main.py` owns application composition and routes. `services.py` coordinates session state, provider calls, prompting, summary extraction, continuity updates, and cleanup. Provider interfaces isolate OpenAI and ElevenLabs from tests. `persona.py` validates and snapshots the active Markdown persona, approach reference, image, voice, and language at session start.

## Data and provider boundaries

Incoming audio is temporary and is deleted after transcription unless debug storage is enabled. Generated speech expires automatically. SQLite and ChromaDB persist until explicitly deleted. RAG failures degrade without interrupting a voice response.

OpenAI receives audio, response prompts, and text selected for embeddings. ElevenLabs receives response text and voice configuration. Credentials never enter frontend responses.

The application is unauthenticated and designed only for a trusted LAN. Internet or multi-user deployments require a separate security design.

## Persona and language

The persona language is the source of truth for UI localization, Whisper hints, LLM output, ElevenLabs text, summaries, topics, safety guidance, and memory retrieval. Persona and approach content is reloaded for each new session and snapshotted so active sessions remain stable.

The tracked persona uses `assets/sandy.jpg`. A host may set `PERSONA_FILE` to an ignored Markdown override and use an ignored portrait inside `config/personas`. Memory retrieval is restricted to exact language matches.

## Storage and migrations

Alembic runs before application startup. Production migrations must remain compatible with the previous code revision because automated rollback restores source but does not downgrade the database. Changing the embedding model requires rebuilding Chroma vectors from SQLite source records.

Runtime paths are installation-specific and supplied through environment variables. The public system installer uses `/var/lib/live-ai-therapy` for state and `/etc/live-ai-therapy` for credentials.

## Deployment pipeline

Branch and pull-request tests use GitHub-hosted runners with fake providers. Only trusted `main` commits may reach the repository-specific self-hosted runner. Deployment transfers a source-only archive over SSH, preserves secrets/data/private persona files, updates dependencies, restarts the service, and checks loopback health. A previous code snapshot is retained for manual rollback.

The repository variable `MX_DEPLOY_ENABLED` must be `true` before deployment. `MX_DEPLOY_PATH` and all SSH values are configured outside source. Public PR code must never run on the self-hosted runner.

## Verification

Run JavaScript tests, Python tests, Alembic head validation, shell syntax validation, and `scripts/check-public-repo.sh`. A real-device acceptance test additionally requires trusted Caddy CA installation, microphone permission, valid provider credentials, and a complete spoken Portuguese turn.
