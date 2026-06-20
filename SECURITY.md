# Security Policy

## Reporting

Do not open a public issue for a vulnerability that could expose credentials, transcripts, memories, or host access. Report it privately through GitHub's security-advisory feature for this repository.

## Deployment boundaries

The supplied deployment is intended for a trusted LAN. It has no application authentication and must not be exposed directly to the Internet. Keep the memory-search debug endpoint disabled.

Secrets belong only in the mode-`600` runtime environment or encrypted GitHub Environment secrets. Never add them to source, workflow YAML, logs, screenshots, issue text, or deployment archives.

The application sends recorded speech and selected prompt context to OpenAI and generated reply text to ElevenLabs. Review the providers' current privacy and retention terms before using real sensitive information.

## Supported versions

Security fixes are applied to the current `main` branch. No older release line is currently maintained.
