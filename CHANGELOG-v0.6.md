# v0.6.0

- Added documented ChatGPT plan-sharing OAuth consent, Windows-protected credential storage, refresh recovery and account model discovery.
- Added GPT conversation with recent TREN history/saved notes; preferred provider becomes ChatGPT after successful sharing consent.
- Added explicit local provider choice and opt-in, labelled Ollama fallback. Coding remains Codex; routines remain Ollama.
- Added Settings controls, safe connection state and persistent reply provider labels with backwards-compatible SQLite migration.
- Added bounded existing-web-tool evidence for explicit/current requests and supplied URLs.
- Preserved previous coding/update functionality and compatible release filenames. No dependency reinstalls or model redownloads.
- Automated protocol/UI/backend checks are distinct from pending Windows live consent, DPAPI and real model verification.
