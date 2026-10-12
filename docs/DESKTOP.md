# Windows desktop setup

## Fresh install — v0.10.0

Download the Windows desktop installer from Releases and open its shortcut. No separate backend extraction is required for new users. The installer bundles a clean backend, Python 3.14.8 embeddable runtime and Node 24.21.0. The launcher prepares a private managed backend/runtime directory under the desktop profile when no existing installation is selected/found. Existing installations and data are retained. Compatible installed Python can be reused; global runtimes are not replaced.

The welcome flow names the personal assistant, connects ChatGPT, then offers optional Codex coding and Ollama/local-model setup. Desktop pairing is performed locally for a new profile; an existing remembered cookie is retained. A revoked cookie for the same installation still requires manual pairing. Assistant names persist in SQLite and can be changed in Settings. Returning profiles retain their setup. The public app name remains TREN until a new brand is chosen.

Optional installers ask for native confirmation. Codex uses the official pinned npm package in a private tools folder when no existing CLI is found; Connect Codex opens its normal browser login. Ollama uses winget if missing, starts/checks its service and downloads qwen3:8b only if absent. These optional paths can require network access, Windows installation prompts and approximately 5 GB for the model. If winget is unavailable, use the official Ollama installer and retry. Settings → Optional tools offers these controls later too.

The themed draggable title bar contains an application-menu button and native window controls. The renderer bridge exposes only theme/menu/allowlisted optional-setup actions; main validates the local sender origin. No arbitrary process/path interface or desktop control token is exposed.

## Existing TREN users

1. In your working TREN, install backend v0.10.0 through Settings → Updates.
2. Download TREN-Desktop-Setup-0.10.0.exe from the same GitHub release. Run the per-user installer; desktop and Start menu shortcuts are created.
3. Open TREN. It uses Desktop/Tren-Local if present, otherwise asks you to select your existing installation folder. That folder must contain app.py, index.html and version.json. It does not copy/reinstall your models, Python or data.
4. If an already-running compatible backend belongs to that folder, the window connects to it. Otherwise it launches the existing Python backend without a console window. The first version uses port 8765, or TREN_PORT when configured in the launching environment.
5. Pair the desktop window once. Native TREN menu → Show pairing code → Copy code displays the local installation's code. Paste it into the pairing screen and leave Remember this device checked. Desktop cookies are separate from browser cookies.

This is an unsigned first installer. Windows may display an unknown-publisher warning; release assets are published under alecjhalpin/TREN. Do not delete your existing Tren-Local folder: this companion still uses it. New users can use the bundled first-launch setup.

## Window, tray and appearance

Closing the window hides it to the tray and keeps work running. Tray double-click/Open TREN restores it. Quit TREN asks before stopping a backend launched by this desktop window; active tasks are cancelled and completed changes remain. If the desktop connected to a separately running backend, quitting closes only the desktop window and says the backend stays running. It does not terminate arbitrary Python processes.

Tray → Launch at Windows sign-in is optional and off by default. The installed app can enable/disable it. A second desktop launch focuses the existing window. Backend startup also retains Windows exclusive port binding.

Settings → Appearance selects Light, Dark or Follow Windows/device. The header toggle switches directly between light and dark. Your preference is stored per browser/desktop profile and survives reload/restart. Follow Windows/device responds to operating-system appearance changes.

## Updates

Backend code/data-compatible updates stay in TREN Settings → Updates. The desktop window reconnects when the backend reloads. Updating the backend does not reinstall the desktop shell.

Native TREN menu or tray → Check desktop updates checks the same public GitHub repository. Download/install each shell update explicitly. Desktop updates replace the shell, preserve the selected backend folder and profile, and stop an owned backend before installation. This update mechanism is implemented; a real subsequent installed-version update still requires acceptance testing.

Keep active work finished/cancelled before a backend update. If a backend update is running, desktop Quit is rejected until the update finishes. Native settings are stored under Electron's TREN user-data directory; backend data remains in the selected installation's data folder.

## Troubleshooting and scope

A mismatched/older server on the port is not silently adopted. Update the intended backend, close its older process and reopen desktop TREN. Missing Python, an invalid folder or startup timeout displays an error; desktop startup output stays in data/updates/desktop.log and can contain the private pairing code. Keep logs local.

The renderer has no Node integration; its isolated preload bridge is limited to validated chrome/setup actions, uses context isolation and Chromium sandboxing, and denies browser permissions. External HTTP(S) links open in the normal browser; other schemes and foreign in-window navigation are blocked. GPT sign-in still uses the system browser and the existing protected connection.

This milestone includes first-install backend/Python/Node packaging. Models and Codex remain optional downloads. It is not a native iPhone app, voice client, visual computer-use driver or animated orb. Local Windows acceptance and CI smoke/build evidence are listed in TESTING.md.

## Verified build and previews

The Windows smoke test and installer build passed in [the release workflow](https://github.com/alecjhalpin/TREN/actions/runs/38248472618). The actual captured window layouts were reviewed: [Light](https://github.com/alecjhalpin/TREN/releases/download/v0.10.0/TREN-Desktop-light.png) / [Dark](https://github.com/alecjhalpin/TREN/releases/download/v0.10.0/TREN-Desktop-dark.png). The preview conversations are synthetic layout fixtures. Local installed-app acceptance remains separate.
