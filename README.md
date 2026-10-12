<div align="center">

# VEYRA

<img src="assets/veyra-hero.jpg" alt="VEYRA silver V and blue glow" width="280">

**Your AI. Your computer. Your rules.**

ChatGPT conversation · Local Ollama fallback · PC tools · Codex coding

[![Release](https://img.shields.io/github/v/release/alecjhalpin/TREN)](https://github.com/alecjhalpin/TREN/releases)
[![Checks](https://github.com/alecjhalpin/TREN/actions/workflows/release.yml/badge.svg)](https://github.com/alecjhalpin/TREN/actions/workflows/release.yml)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4)
![Status](https://img.shields.io/badge/status-early_development-orange)

[Download](https://github.com/alecjhalpin/TREN/releases/latest) · [Setup](#getting-started) · [Updates](#updating-veyra) · [Roadmap](ROADMAP.md)

</div>

---

VEYRA is a Windows-first assistant with a conversational browser interface. Talk through an idea, work on a coding project, or ask it to inspect your PC and carry out reviewed actions. Notes, task history and settings stay on your machine; ChatGPT requests use the cloud, while Ollama provides a local conversation option.

## What VEYRA can do

| | Capabilities |
| --- | --- |
| **Conversation** | ChatGPT through eligible-plan sharing, with optional Ollama fallback. |
| **PC tasks** | Inspect drives and files, manage files, and run reviewed PowerShell commands. Requested administrator commands use Windows UAC. |
| **Coding** | Queue project-scoped Codex tasks using your existing ChatGPT CLI login. |
| **Continuity** | Saved notes, reminders, task results and remembered, revocable device sessions. |
| **Updates** | Download releases inside VEYRA, back up app files and restart while preserving your data. |

## What's new in v0.11.0

- **VEYRA branding:** application name, welcome artwork, desktop/menu/tray labels and installer branding now use VEYRA.
- **New app icon and blue accents:** a transparent V icon accompanies restrained blue highlights in both themes.
- **Your assistant, your name:** new assistants start with Nova as the example; custom names and returning TREN identities remain intact.
- **Compatible transition:** desktop profiles, backend data, pairing, credentials, models and the existing update repository/ZIP format are preserved.

The application is VEYRA; your assistant can have any supported name. The GitHub repository remains `alecjhalpin/TREN`. Backend ZIPs retain `TREN-vVERSION.zip` so existing updaters can install the rebrand.

## Getting started

### New Windows installation

1. Download **VEYRA-Desktop-Setup-0.11.0.exe** from [Releases](https://github.com/alecjhalpin/TREN/releases/latest) and run it.
2. Open the desktop shortcut. The app prepares its bundled backend/runtimes if no existing installation is found.
3. Choose your assistant's name and connect ChatGPT in the welcome flow. No API key is configured for this connection; eligible-plan limits apply.
4. Optionally install/check Codex and connect its separate ChatGPT CLI login. Choose local AI only if you want Ollama and its roughly 5 GB default model download.

Basic ChatGPT/PC-agent setup no longer needs a separate Python/Node installation or mandatory Ollama download. Existing compatible Python installations can be reused; bundled runtime files do not replace global installations. Optional Ollama setup uses Windows winget and may show its installer/UAC prompt. See [Desktop setup](https://github.com/alecjhalpin/TREN/blob/main/docs/DESKTOP.md).

### Existing TREN users

Update the backend through Settings → Updates first, then update/install the desktop shell. Keep your existing Tren-Local folder: data, auth, projects and models remain there. Rename your assistant under Settings → Your assistant. Returning users are not forced through a fresh setup.

### Source/browser setup

The release ZIP and setup.bat remain available for manual/source installations. Python 3.11+ is required for this route; setup.bat installs missing Python/Ollama and downloads the default model. Do not rerun setup.bat to update an existing installation. The default local model is qwen3:8b.

## Updating VEYRA

For installations with in-app updates: **Settings → Updates → Check for updates → Download update → Install & restart**. Use repository `alecjhalpin/TREN`.

Updates preserve current data, pairing secrets, projects, host settings and installed models. Finish or cancel active work first. **Do not rerun setup to upgrade.**

<details>
<summary>Older installations and troubleshooting</summary>

For older installations without the updater, stop TREN, extract the release asset into a new folder and run `upgrade.bat`. It detects the standard Desktop/Tren-Local installation or asks you to select it. Then start the existing installation.

If an update fails its startup check, inspect `data/updates/restart.log` in the installed TREN folder. The updater attempts to restore the previous code; check the displayed installed version before retrying. Keep your data and backup folders.

</details>

## What's next

Further desktop polish, private iPhone access, voice, and an animated orb interface are planned. Visual desktop/browser automation is also future work. The desktop companion wraps the current conversation interface; a native iPhone app and voice are not delivered.

[Roadmap and v1.0 criteria](ROADMAP.md) · [Private phone setup](PHONE-SETUP.md) · [ChatGPT integration details](https://github.com/alecjhalpin/TREN/blob/main/docs/TECHNICAL.md)

## Documentation

[Setup and updates](#getting-started) · [Phone setup](PHONE-SETUP.md) · [Technical guide](https://github.com/alecjhalpin/TREN/blob/main/docs/TECHNICAL.md) · [Testing and acceptance](https://github.com/alecjhalpin/TREN/blob/main/docs/TESTING.md) · [Changelog](CHANGELOG.md)

## Development

Python standard-library backend, SQLite storage and a single-file frontend.

```sh
python build_release.py TREN-v0.11.0.zip
python -m unittest discover -s tests -v
node tests/ui_logic.cjs
```

Build first to generate the release manifest needed by updater tests. Backend tests use mock services and fake CLI fixtures; UI checks cover logic rather than rendered browser behavior.

<details>
<summary>Release conventions and repository hygiene</summary>

Main pushes and manual workflow runs build, validate and test the release. A version is published only if it does not already exist; existing release assets are never overwritten. For each new release, increment `version.json` and replace the “What's new” section with that release's added features. Append older history to CHANGELOG.md; do not add per-version README or changelog files.

Never commit `data/`, backups, `allowed-hosts.txt`, credentials, pairing secrets, logs or personal project notes. Keep 0.x versions while reliability and capabilities mature; [ROADMAP.md](ROADMAP.md) defines v1.0 readiness.

</details>
