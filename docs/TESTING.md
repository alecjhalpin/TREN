# TREN testing and acceptance

## Current automated baseline

v0.9.0: 80 backend tests pass on the Linux development environment; Node UI logic checks pass. Desktop publication is gated on a real Windows Electron smoke test and NSIS build. Run the manifest builder before the backend suite:

```sh
python build_release.py TREN-v0.9.0.zip
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

Reviewed temporary-file changes, harmless PowerShell commands, task denial/cancellation and explicitly requested UAC diagnostics on Windows; private iPhone/Tailscale/Safari use; broader rendered/browser accessibility checks; full failure/recovery and duplicate-launch scenarios. Desktop packaging is implemented with acceptance pending; native phone app, voice and visual browser/desktop control remain planned.

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
