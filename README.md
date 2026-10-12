# TREN

Windows-first personal assistant with a conversational browser UI, ChatGPT plan-sharing conversation, local Ollama fallback, Plus-authenticated Codex coding tasks, saved notes, reminders and in-app updates.

## What's new in v0.6.0

- **ChatGPT conversation:** connect your account in Settings to use eligible plan usage for everyday chat.
- **TREN context:** saved notes and recent chat are included in GPT conversations.
- **Provider choice:** choose ChatGPT or local Ollama, with optional, clearly labelled Ollama fallback.
- **Model selection:** discover and choose models available to your connected account.
- **Web evidence:** explicit searches, current-information requests and supplied URLs can provide read-only evidence for GPT replies.
- **Clear reply labels:** see whether ChatGPT, Ollama or a local command produced each response.

Coding continues through Codex; scheduled routines continue through Ollama. See [v0.6 details](README-v0.6.md) for setup and limitations.

## Updates

Current release: v0.6.0. Download the TREN-vX.Y.Z.zip asset from [Releases](https://github.com/alecjhalpin/TREN/releases), not the GitHub source-code ZIP.

Existing v0.5 installations: Settings → Updates → enter `alecjhalpin/TREN` → Check for updates → Download update → Install & restart. Current v0.6.0 defaults to this repository when no preference is saved. Code backups and database snapshots are created; current data, pairing secret, projects, hosts and model installations remain intact. Pairing sessions currently reset on restart.

Older installations need a one-time updater bootstrap: stop TREN, extract the release asset into a new folder, run upgrade.bat, then start TREN from the existing installation. Standard Desktop/Tren-Local is detected; otherwise select the installation folder. No dependency reinstall needed for upgrades.

## First-time setup

Python 3.11+, Ollama and a tool-capable local model (default qwen3:8b) are needed. setup.bat installs missing Python/Ollama and downloads the model for first-time users. Codex coding needs an installed CLI and ChatGPT login; no API key is used. Never run setup.bat merely to upgrade an existing installation. Read README-v0.6.md for current limitations and PHONE-SETUP.md for private Tailscale phone access.

## Development

Python standard library backend and single-file frontend. `python build_release.py TREN-v0.6.0.zip` generates a manifest-verified release package. Then `python -m unittest discover -s tests -v`; `node tests/ui_logic.cjs` runs logic-only UI checks. Backend tests use mock services/fake CLI; real Windows integration must be verified locally. Rendered browser QA is separate.

The release workflow runs on main pushes or manual dispatch. It validates/builds/tests the version and publishes a release only if that version does not already exist. For every new release, increment version.json and replace the README’s “What's new” section with that version’s newly added features. Keep older release history in versioned changelogs. It never overwrites an existing release asset.

Do not commit data/, backups/, allowed-hosts.txt, auth files, pairing secrets, logs or personal project notes. This repository contains clean source and synthetic tests only. ChatGPT conversation is implemented in v0.6.0. Connect in Settings using the documented plan-sharing consent flow. Windows and Node.js are required for protected sign-in and identity verification; no extra npm/pip install is needed. Persistent device sessions, desktop/iPhone packaging, voice and an animated orb interface remain future work. Read README-v0.6.md for integration limits and verification status.
