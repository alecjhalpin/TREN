# TREN

Windows-first personal assistant with a conversational browser UI, ChatGPT plan-sharing conversation, local Ollama fallback, Plus-authenticated Codex coding tasks, saved notes, reminders and in-app updates.

## What's new in v0.8.0

- **General PC agent:** GPT chooses tools, uses actual results and continues across multiple steps; new tasks do not need a custom feature for each command.
- **Live PC inspection:** ask about free storage across drives, basic system information, files or folders.
- **Broad file access:** search/read/stat, create/edit/copy/move files and create folders under your Windows account.
- **PowerShell tasks:** run installed programs and general scripts through a reviewed action in the conversation.
- **Administrator tasks:** approved elevated commands use Windows UAC for that task, without elevating the TREN web server.
- **Action review and history:** approve/deny a specific action, cancel a task, inspect results, and retain interrupted/partial-task records.
- **File backups:** supported file edits/moves/deletions save originals and verify results; general scripts do not have automatic rollback.
- **Startup protection:** a second instance cannot interrupt the first instance’s jobs by reinitializing their state.

Native visual browser/desktop automation, the desktop app and voice remain future work. See [v0.8 details](README-v0.8.md) for access, limits and verification.

## Updates

Current release: v0.8.0. Download the TREN-vX.Y.Z.zip asset from [Releases](https://github.com/alecjhalpin/TREN/releases), not the GitHub source-code ZIP.

Existing v0.5 installations: Settings → Updates → enter `alecjhalpin/TREN` → Check for updates → Download update → Install & restart. Current v0.8.0 defaults to this repository when no preference is saved. Code backups and database snapshots are created; current data, pairing secret, projects, hosts and model installations remain intact. Remembered v0.7 devices stay paired across this update; temporary sessions need pairing again.

Older installations need a one-time updater bootstrap: stop TREN, extract the release asset into a new folder, run upgrade.bat, then start TREN from the existing installation. Standard Desktop/Tren-Local is detected; otherwise select the installation folder. No dependency reinstall needed for upgrades.

## First-time setup

Python 3.11+, Ollama and a tool-capable local model (default qwen3:8b) are needed. setup.bat installs missing Python/Ollama and downloads the model for first-time users. Codex coding needs an installed CLI and ChatGPT login; no API key is used. Never run setup.bat merely to upgrade an existing installation. Read README-v0.8.md for current limitations and PHONE-SETUP.md for private Tailscale phone access.

## Development

Python standard library backend and single-file frontend. `python build_release.py TREN-v0.8.0.zip` generates a manifest-verified release package. Then `python -m unittest discover -s tests -v`; `node tests/ui_logic.cjs` runs logic-only UI checks. Backend tests use mock services/fake CLI; real Windows integration must be verified locally. Rendered browser QA is separate.

The release workflow runs on main pushes or manual dispatch. It validates/builds/tests the version and publishes a release only if that version does not already exist. For every new release, increment version.json and replace the README’s “What's new” section with that version’s newly added features. Keep older release history in versioned changelogs. It never overwrites an existing release asset.

Do not commit data/, backups/, allowed-hosts.txt, auth files, pairing secrets, logs or personal project notes. This repository contains clean source and synthetic tests only. ChatGPT conversation is implemented in v0.6.0. Connect in Settings using the documented plan-sharing consent flow. Windows and Node.js are required for protected sign-in and identity verification; no extra npm/pip install is needed. Persistent revocable device sessions are implemented in v0.7.0. Desktop/iPhone packaging, voice and an animated orb interface remain future work. Read README-v0.6.md for integration limits and verification status.

## Release direction

Continue 0.x releases while core agent capabilities and reliability mature. v1.0 is reserved for a dependable daily-use assistant with verified PC tasks, desktop launch, phone access and the agreed voice/experience work. See ROADMAP.md for completion criteria.
