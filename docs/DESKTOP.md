# VEYRA desktop

The Windows Electron application launches the local Python/SQLite backend without a routine terminal window. Its bundled Python and Node runtimes are private to VEYRA; it does not replace global installations. Optional Codex and Ollama setup remain separate downloads. The installer offers a folder picker and a checked-by-default desktop shortcut option; silent updates preserve shortcut opt-out.

## Install and launch

Run the Windows installer from the release page, open VEYRA, name your assistant and connect ChatGPT in the welcome flow. Returning users retain their existing name, settings and selected backend. Basic GPT conversation and PC tools do not require Ollama. Voice models download on first use and remain cached locally. Browser tools use a dedicated Microsoft Edge profile on Windows; existing browser cookies are not copied. If Edge has been removed, restore Edge before using browser tools.

Closing the window keeps VEYRA in the tray. Tray Open restores it; Quit confirms stopping owned background work. Launch at sign-in is optional. Light/dark/system appearance is remembered. The native title bar, mode picker and voice/orb controls are part of the conversation UI.

## Complete-package updates

Settings → Updates → **Update VEYRA** checks the built-in repository, downloads the newer desktop package and asks before installing/restarting. The normal desktop flow has no repository or ZIP field. The native menu/tray uses the same updater. Installation stops the backend owned by this desktop window; completed changes remain. If the desktop attached to an independently running backend, stop that backend before reopening an upgraded app.

On startup, the bundled backend upgrade uses a verified manifest and code/database backups. Existing data, provider credentials, projects and cached models stay in the selected backend folder. Source/browser installations retain the backend ZIP updater and manual recovery scripts. Do not rerun setup to update an existing installation.

## Voice

Click the microphone; click again to end recording, or allow silence detection to stop it. Settings offers microphone selection, background-noise calibration, local neural/device speech, voice/rate previews, automatic sending and spoken-reply preferences. Mute and Stop voice interrupt output. Calibration records only a short local noise sample; there is no wake word or background listener.

Whisper and Kokoro run locally on CPU after model setup. Recognized text goes to the selected conversation provider, so GPT conversation still uses the cloud. Physical device quality and real voice latency must be checked on the user's PC; fake-device CI and generated-audio round trips do not certify those.

## Automatic and administrator access

Review, inspect and off remain available. Automatic whole-PC access requires a warning and explicit confirmation. The elevated worker has a separate warning and one-time normal Windows UAC setup for the same signed-in administrator account. It uses a per-user Task Scheduler task at highest privilege. System UAC is not disabled; standard-account credential elevation to another user is not supported by this mechanism. Disable/revoke and Stop All remain available.

## Compatibility and troubleshooting

Visible program folders and shortcuts use VEYRA. Legacy executable `TREN.exe`, appId `com.alecjhalpin.tren`, Electron profiles, environment variables and backend storage locations remain compatible to protect existing installations. Do not rename/delete a working Tren-Local data folder. Current backend release assets use `VEYRA-vVERSION.zip`; historical asset names remain in old releases.

A foreign or incompatible server on the port is rejected. Startup logs are local under `data/updates/desktop.log`; keep them private because they may contain pairing information. A failed update retains backups and recovery logs. The renderer has context isolation, sandboxing and no Node integration; only local audio/notification permissions and narrowly validated desktop actions are exposed. External links open in the system browser.

See [Testing](TESTING.md) for exact CI evidence and remaining installed-PC acceptance. Native phone, wake-word and arbitrary visual desktop-control features are not delivered.
