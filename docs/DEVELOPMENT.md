# Integrated v0.12 release acceptance

Approved 2026-10-12: one integrated mega-update. `mega-update` is the development branch; v0.11.1 stays stable until the candidate implementation and release checks pass. Phone capability and a wake word are outside this release.

## Scope and evidence

| Area | Implemented behavior | Verification |
| --- | --- | --- |
| Permissions | Whole-PC auto requires warning/checkbox confirmation; review/inspect/off, action-bound review, revocation | Backend/unit checks; real Electron consent checks in candidate CI |
| Elevation | Authenticated per-user Highest interactive worker after one-time UAC; disable/revoke/parent-lifetime checks | Previous Windows candidate installed pinned rimraf/glob, executed it and verified revocation; user's interactive enrollment is separate |
| Scheduling | Five-field local/UTC cron, reusable workflows, coalescing, no overlap; failed/uncertain prior runs pause | Real SQLite/unit checks; model-generated recurring-work quality needs user acceptance |
| Memory | Agent-scoped CRUD, pinned context, priority/recency; GPT Chat memory without PC actions | SQLite/provider fixtures including isolation and Chat/off mode |
| MCP | Pooled stdio/streamable HTTP, tool discovery/calls, lifecycle/timeout/cancel, protected configs | Real local stdio and HTTP server tests; no claim of every external MCP service/OAuth flow |
| Browser | Dedicated Edge/Playwright profile, references, navigation/actions, previews, upload/download, cancellation | Earlier Windows navigation/fill/click/extraction passed; expanded acceptance is running |
| Agents | Independent contexts/workspaces, recursive children under shared budgets, serial workspace access | SQLite/blocked-provider/cancellation/recovery tests |
| Workspace | Traversal-bound listing, text/image preview and reference | Unit/desktop UI checks; whole-PC agents are not OS sandboxes |
| Voice/orb | Click mic, Whisper/Kokoro, device/rate selection, noise calibration, mute/interruption | Real generated-speech round trip and Electron fake-device capture passed earlier; physical devices/latency remain user acceptance |
| Activity | Inbox, notifications, Stop All, provider cancellation, root watchdog and limits | Unit/MCP/desktop checks; selected foreign backends are not silently killed |
| Recovery | Durable checkpoints, descendant mutation ledger, uncertain-action reporting, explicit continuation | Unit/process tests; arbitrary shell effects cannot promise automatic undo |
| Backup | Agents/memory/workflows/limits/settings export/restore, paused restore, no credentials/session/elevation keys | SQLite/private-settings/workspace-collision checks |
| Updates | Built-in repo, one desktop button, download then restart confirmation, manifest-backed backend migration | Backend integrity/rollback checks; final installed package/upgrade acceptance pending |
| Installer | Bundled Python/Node/browser/voice dependencies, folder/shortcut opt-out, legacy data/profile preservation | Earlier staging/NSIS tests passed; corrected actual dependency packaging must pass final Windows CI |
| Program install | Small pinned CLI plus dependencies, actual execution and revocation | Real elevated Windows worker installed rimraf 6.0.1 plus glob, removed owned fixture and verified resulting state |

## Current checkpoint

The ordinary local suite passes **107 Python tests with three opt-in tests skipped** (104 passed); desktop/runtime Node checks pass 10 with two Windows-only checks skipped. Composer logic and JavaScript syntax checks pass. Manifest generation and the real SQLite upgrade/rollback checks pass. These are implementation checks, not live account/device acceptance.

Remote checkpoint `6043520ae8abd58c63bc7a6442f5658f68e22ca9` passed Windows run [38311670256](https://github.com/alecjhalpin/Veyra/actions/runs/38311670256), including real Edge actions, Whisper/Kokoro round trip, authenticated elevated program installation, fake-device audio capture, fresh/existing desktop launch and installer options/profile preservation.

Review afterward found electron-builder's root `node_modules` exclusion. Explicit resource mappings now include tool dependencies and bundled npm; installed-package checks must verify native imports and actual window launch. The expanded Edge fixture also required bounded worker shutdown/diagnostics. Recovery checkpoint `427b475` passed Linux validation; its stalled Windows fixture was cancelled for corrected run `38319199037`. Latest candidate acceptance remains in progress; do not infer success from a timer or a previous source SHA.

## Architecture and upstream reuse

Keep Python/SQLite, existing eligible-plan GPT sharing, optional Ollama and project-scoped Codex. Add a private pooled Node process for Playwright/MCP/local inference, a bounded durable agent/workflow engine, voice workbench and a separately enrolled elevated worker. Children cannot exceed parent tool permissions; root budgets cover the complete tree. Preserve original data/auth/projects and legacy internal identities.

Golemancy inspected at `d39b6620414a022b0a0a6707b8861322ea251826` (Apache-2.0). The small accessibility snapshot formatter is adapted with attribution in `vendor/golemancy`; its backend/provider/telemetry code is not incorporated. Browser automation does not imply arbitrary native visual computer use.

## Release gate

Publish only after candidate source checks, real Windows runtime/voice/browser tests, actual packaged-dependency checks, fresh/upgrade/installer preservation, and reviewed UI captures pass. Update README/current feature list and the single changelog, plus private continuity references. A branch push cannot publish; the release job is main-only and depends on validation and desktop acceptance.

After installation, separately confirm the real GPT account, physical microphone/speakers, interactive UAC enrollment, and a daily-use workflow. CI uses synthetic identity/layout fixtures and an already-elevated disposable runner; label those limits clearly. Keep 0.12 rather than claiming v1.0 maturity from feature count.
