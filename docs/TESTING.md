# VEYRA testing and acceptance

## Current automated baseline

v0.11.0: 83 backend tests and 6 desktop tests pass on the Linux development environment; Node UI logic checks pass. Desktop publication is gated on a real Windows Electron smoke test and NSIS build. Run the manifest builder before the backend suite:

```sh
python build_release.py TREN-v0.11.0.zip
python -m unittest discover -s tests -v
node tests/ui_logic.cjs
```

The suite uses temporary data, synthetic credentials, mocked providers and fake Codex subprocesses. Coverage includes authentication/host/origin checks, pairing persistence/revocation, reminders/memory, web address checks, coding queue/artifacts/cancellation/restart, update integrity/data preservation/rollback, GPT OAuth/signature/refresh/model/stream behavior, PC file/backups/approvals/tool continuation, and authenticated/validated Auto routing that cannot submit work itself.

UI checks use a minimal DOM simulator. They cover the composer, safe formatting, task approval controls, explicit mode overrides, synthetic Auto routing and update flows. They do not certify browser layout, native events or actual model decision quality. Windows DPAPI/PowerShell/UAC and process-tree behavior require real local acceptance.

## User-confirmed Windows behavior

- Installed Codex/ChatGPT login, successful project file creation/preview and local execution; follow-up edits, cancellation and restart recovery were reported working in earlier milestones.
- Basic GPT conversation and v0.7 composer/device behavior were reported working.
- Closing duplicate TREN processes resolved the initial v0.8 startup-check rollback; the Windows listener exclusivity correction followed in v0.8.1.
- v0.8.2 returned correct live drive-storage results after the completed-stream-item parser correction.
- The cleaner conversation formatting was preferred after v0.8.3.
- The user reported v0.8.4 Auto routing works. This is functional acceptance, not an exhaustive classification/latency evaluation.

## Still to verify

Explicitly requested UAC diagnostics on Windows; private iPhone/Tailscale/Safari use; broader rendered/browser accessibility checks; full failure/recovery and duplicate-launch scenarios. Windows packaging and existing/fresh bootstrap smoke passed; installed-version upgrade and user lifecycle acceptance remain pending; native phone app, voice and visual browser/desktop control remain planned.

## Useful local acceptance checks

1. In Auto, send a greeting: expect ordinary chat without a PC job.
2. Ask for drive storage: compare actual drive results with Windows.
3. Ask to create a disposable Desktop file: inspect the proposed action, approve it and independently inspect the file.
4. Deny a proposed change: verify it did not run. Cancel a harmless long-running task and inspect any completed steps before retrying.
5. Request a project calculator: review project/permissions/expected files, then independently run the inspected output expecting 4.
6. Restart/update with remembered pairing and a saved note; confirm both survive. Launch a second instance and confirm it does not reinitialize active jobs.

## Historical automated milestones

| Version | Recorded backend tests | Scope |
| --- | ---: | --- |
| 0.3 | 30 | Initial Codex integration and existing app/update regressions |
| 0.4 | 33 | Conversation/composer and follow-up/restart checks |
| 0.5 | 45 | In-app updater validation and Linux real-process update/rollback |
| 0.8.0 | 76 | General PC agent and approval/elevation fixtures |
| 0.8.1 | 77 | Distinct tool-response diagnostics |
| 0.8.2–0.8.3 | 78 | Completed streamed output items and conversation layout |
| 0.8.4 | 79 | Authenticated semantic-routing control flow |

These counts record checks run at those milestones, not guarantees that every feature was tested on Windows. Older reports and exact sources remain in Git history/releases.

## Desktop verification

Four Node transport/installation/navigation/version tests pass locally, plus theme selection/persistence/system-change UI logic. The Python suite checks desktop controller authentication, host/origin/confirmation gates and shutdown dispatch. The Windows workflow starts the actual Electron window and Python backend, checks light/dark and reload persistence, pairs synthetic local data, captures layout previews, and stops the owned backend without inference/model calls. Build results and user desktop acceptance must be reported separately.

Pending installed-PC acceptance: installer/shortcuts, tray close/open/quit, launch at sign-in, remembered desktop pairing, continued GPT/tool use, backend update/reconnect, and an actual later desktop-shell update. User reported successful file creation, action denial, harmless PowerShell execution and cancellation before desktop development; UAC remains a separate pending test.

Windows build evidence: [Actions run 38248472618](https://github.com/alecjhalpin/TREN/actions/runs/38248472618) passed backend validation, the actual Electron/Python Windows smoke test, theme reload persistence, pairing with temporary CI data, authenticated owned-backend shutdown, and NSIS installer packaging. Both captured light/dark layouts were visually reviewed after publication. These use synthetic preview conversation content, not a live GPT session. Installer/shortcuts/tray/startup and later updater acceptance on the user's PC remain pending. A separate real-process Linux desktop-controller startup/status/graceful-shutdown check also passed without model calls.

## v0.10.0 acceptance scope

Adds backend profile authentication/validation/persistence and returning-user migration tests, a private-runtime bootstrap preservation test, and UI logic checks. The Windows workflow now covers both an existing installation and a new managed backend using bundled Python/Node, as well as theme/window/onboarding smoke checks. Optional Codex/Ollama downloads and real account consent are not run by CI. Fresh installed-PC setup, provider consent, optional installs and public-brand selection remain separate user acceptance items.

Windows v0.10.0 build evidence: [Actions run 38252658975](https://github.com/alecjhalpin/TREN/actions/runs/38252658975) passed both existing-folder and fresh managed-backend smoke tests, bundled-runtime startup, actual onboarding name/skip/finish handlers, themed window/menu controls, theme persistence, picker selection, authenticated shutdown and NSIS packaging. The light/dark, mode-menu and welcome screenshots were reviewed after publication. Their conversations are synthetic fixtures, not live inference. Optional installer downloads and actual account consent remain installed-PC acceptance items.

## v0.11.0 brand transition

Added regression checks for new Nova identity, retaining returning TREN/custom identities and selecting legacy desktop profiles in place. Backend/desktop versions must match. Windows builds exercise existing and fresh bootstrap, rendered light/dark/welcome/menu screenshots and installer packaging. CI does not prove a real installed v0.10→v0.11 upgrade, shortcut/Windows sign-in migration, or new live OAuth consent; those remain user acceptance checks.

Actions 38258749000 verified backend/UI/desktop tests, both Windows bootstrap smoke modes and NSIS packaging, then published v0.11.0. Dark and onboarding captures were reviewed. Its published light screenshot captured a stale hidden-window frame and is not a valid light preview; the capture harness now shows the test window and waits for rendered frames, checking the actual computed background before capture. This is test-harness validation, not a model-inference claim.

Follow-up Actions 38259481391 passed all checks and both visible Windows smoke modes with computed light/dark background assertions. Existing v0.11.0 release assets were retained. Installed upgrade/user acceptance remains separate.
