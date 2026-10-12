# TREN testing and acceptance

## Current automated baseline

v0.8.4: 79 backend tests pass on the Linux development environment; Node UI logic checks pass. GitHub's release workflow also passed. Run the manifest builder before the backend suite:

```sh
python build_release.py TREN-v0.8.4.zip
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

Reviewed temporary-file changes, harmless PowerShell commands, task denial/cancellation and explicitly requested UAC diagnostics on Windows; private iPhone/Tailscale/Safari use; broader rendered/browser accessibility checks; full failure/recovery and duplicate-launch scenarios. Desktop packaging, native phone app, voice and visual browser/desktop control are planned and have no delivered-feature acceptance claim.

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
