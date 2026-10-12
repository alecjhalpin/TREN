<div align="center">

# ◉ TREN

**Your personal AI agent. Conversation first. Built for your PC.**

ChatGPT conversation · Local Ollama fallback · PC tools · Codex coding

[![Release](https://img.shields.io/github/v/release/alecjhalpin/TREN)](https://github.com/alecjhalpin/TREN/releases)
[![Checks](https://github.com/alecjhalpin/TREN/actions/workflows/release.yml/badge.svg)](https://github.com/alecjhalpin/TREN/actions/workflows/release.yml)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4)
![Status](https://img.shields.io/badge/status-early_development-orange)

[Download](https://github.com/alecjhalpin/TREN/releases/latest) · [Setup](#getting-started) · [Updates](#updating-tren) · [Roadmap](ROADMAP.md)

</div>

---

TREN is a Windows-first assistant with a conversational browser interface. Talk through an idea, work on a coding project, or ask it to inspect your PC and carry out reviewed actions. Notes, task history and settings stay on your machine; ChatGPT requests use the cloud, while Ollama provides a local conversation option.

## What TREN can do

| | Capabilities |
| --- | --- |
| **Conversation** | ChatGPT through eligible-plan sharing, with optional Ollama fallback. |
| **PC tasks** | Inspect drives and files, manage files, and run reviewed PowerShell commands. Requested administrator commands use Windows UAC. |
| **Coding** | Queue project-scoped Codex tasks using your existing ChatGPT CLI login. |
| **Continuity** | Saved notes, reminders, task results and remembered, revocable device sessions. |
| **Updates** | Download releases inside TREN, back up app files and restart while preserving your data. |

## What's new in v0.8.2

- **Streamed tool responses:** retain completed output items and reasoning from the stream when the final completion does not repeat them. Tool calls still require a successfully completed response.
- **Clearer Auto mode:** the selector says “Auto · chat + PC tools”; completed responses without tool actions appear as ChatGPT conversation.

**Verification:** ordinary conversation works on the user's Windows installation. The parser fix passes synthetic streaming regressions; live storage/tool-call acceptance remains pending. Auto uses GPT with available PC tools, while explicit ChatGPT and Chat modes use regular conversation.

## Getting started

1. Download **TREN-vX.Y.Z.zip** from [Releases](https://github.com/alecjhalpin/TREN/releases/latest) and extract it.
2. For a first installation, run `setup.bat` to install missing Python/Ollama and download the default local model.
3. Run `start.bat`, open TREN and pair using the displayed code.
4. Connect ChatGPT in Settings. Coding tasks additionally need the installed Codex CLI signed in with ChatGPT.

Python 3.11+ is required. Windows and Node.js are required for protected ChatGPT sign-in and identity verification. The default Ollama model is `qwen3:8b`. ChatGPT usage depends on your eligible plan and its limits; TREN does not use an API key for this connection.

## Updating TREN

For installations with in-app updates: **Settings → Updates → Check for updates → Download update → Install & restart**. Use repository `alecjhalpin/TREN`.

Updates preserve current data, pairing secrets, projects, host settings and installed models. Finish or cancel active work first. **Do not rerun setup to upgrade.**

<details>
<summary>Older installations and troubleshooting</summary>

For older installations without the updater, stop TREN, extract the release asset into a new folder and run `upgrade.bat`. It detects the standard Desktop/Tren-Local installation or asks you to select it. Then start the existing installation.

If an update fails its startup check, inspect `data/updates/restart.log` in the installed TREN folder. The updater attempts to restore the previous code; check the displayed installed version before retrying. Keep your data and backup folders.

</details>

## What's next

Desktop launch without a terminal, private iPhone access, voice, and an animated orb interface are planned. Visual desktop/browser automation is also future work. TREN currently uses a browser interface; these plans are not delivered desktop or iPhone apps.

[Roadmap and v1.0 criteria](ROADMAP.md) · [Private phone setup](PHONE-SETUP.md) · [ChatGPT integration details](README-v0.6.md)

## Development

Python standard-library backend, SQLite storage and a single-file frontend.

```sh
python build_release.py TREN-v0.8.2.zip
python -m unittest discover -s tests -v
node tests/ui_logic.cjs
```

Build first to generate the release manifest needed by updater tests. Backend tests use mock services and fake CLI fixtures; UI checks cover logic rather than rendered browser behavior.

<details>
<summary>Release conventions and repository hygiene</summary>

Main pushes and manual workflow runs build, validate and test the release. A version is published only if it does not already exist; existing release assets are never overwritten. For each new release, increment `version.json` and replace the “What's new” section with that release's added features. Preserve older history in versioned documentation.

Never commit `data/`, backups, `allowed-hosts.txt`, credentials, pairing secrets, logs or personal project notes. Keep 0.x versions while reliability and capabilities mature; [ROADMAP.md](ROADMAP.md) defines v1.0 readiness.

</details>
