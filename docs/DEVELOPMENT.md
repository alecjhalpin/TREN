# Integrated v0.12 release acceptance

Approved 2026-10-12: one integrated mega-update. The integrated v0.12 implementation passed candidate acceptance; main-only publication remains gated on the final release run. Phone capability and a wake word are outside this release.

## Scope and evidence

| Area | Implemented behavior | Verification |
| --- | --- | --- |
| Permissions | Whole-PC auto requires warning/checkbox confirmation; review/inspect/off, action-bound review, revocation | Backend/unit checks; real Electron consent checks in Windows CI |
| Elevation | Authenticated per-user Highest interactive worker after one-time UAC; disable/revoke/parent-lifetime checks | Windows acceptance installed pinned rimraf/glob, executed it and verified revocation; user's interactive enrollment is separate |
| Scheduling | Five-field local/UTC cron, reusable workflows, coalescing, no overlap; failed/uncertain prior runs pause | Real SQLite/unit checks; model-generated recurring-work quality needs user acceptance |
| Memory | Agent-scoped CRUD, pinned context, priority/recency; GPT Chat memory without PC actions | SQLite/provider fixtures including isolation and Chat/off mode |
| MCP | Pooled stdio/streamable HTTP, tool discovery/calls, lifecycle/timeout/cancel, protected configs | Real local stdio and HTTP server tests; no claim of every external MCP service/OAuth flow |
| Browser | Dedicated Edge/Playwright profile, references, navigation/actions, previews, upload/download, cancellation | Real Windows navigation/fill/click/extraction, password masking, screenshot, upload/download and cancellation passed |
| Agents | Independent contexts/workspaces, recursive children under shared budgets, serial workspace access | SQLite/blocked-provider/cancellation/recovery tests |
| Workspace | Traversal-bound listing, text/image preview and reference | Unit/desktop UI checks; whole-PC agents are not OS sandboxes |
| Voice/orb | Click mic, Whisper/Kokoro, device/rate selection, noise calibration, mute/interruption | Real generated-speech round trip and Electron fake-device capture passed; physical devices/latency remain user acceptance |
| Activity | Inbox, notifications, Stop All, provider cancellation, root watchdog and limits | Unit/MCP/desktop checks; selected foreign backends are not silently killed |
| Recovery | Durable checkpoints, descendant mutation ledger, uncertain-action reporting, explicit continuation | Unit/process tests; arbitrary shell effects cannot promise automatic undo |
| Backup | Agents/memory/workflows/limits/settings export/restore, paused restore, no credentials/session/elevation keys | SQLite/private-settings/workspace-collision checks |
| Updates | Built-in repo, one desktop button, download then restart confirmation, manifest-backed backend migration | Backend integrity/rollback checks; actual installed package/upgrade acceptance passed |
| Installer | Bundled Python/Node/browser/voice dependencies, folder/shortcut opt-out, legacy data/profile preservation | Actual installed native imports/npm/window launch and folder/shortcut/legacy profile upgrade acceptance passed |
| Program install | Small pinned CLI plus dependencies, actual execution and revocation | Real elevated Windows worker installed rimraf 6.0.1 plus glob, removed owned fixture and verified resulting state |

## Current checkpoint

Verified source checkpoint `0f4b8fa296901604b6f4aa7312f5d28ab53ba78b`: [Actions 38323184389](https://github.com/alecjhalpin/Veyra/actions/runs/38323184389) passed Linux validation and Windows acceptance. The ordinary Python suite has 108 tests: 105 passed and three opt-in checks skipped locally; all three opt-in voice/admin checks passed on Windows. Node runtime/desktop checks passed 10 locally with two Windows skips and all 12 on Windows. Composer and syntax checks passed. Windows verified Edge actions, cold local voice preview and recognition, private native C++ runtime loading, elevated rimraf/glob installation and execution, Task Scheduler enrollment/revocation, microphone capture/calibration with a fake device, actual installed dependency imports and app launch, and installer/upgrade/profile/shortcut preservation. Physical microphone/speaker quality, the real GPT account, interactive user UAC consent and overnight daily-use workflows remain separate user acceptance.

## Architecture and upstream reuse

Keep Python/SQLite, existing eligible-plan GPT sharing, optional Ollama and project-scoped Codex. Add a private pooled Node process for Playwright/MCP/local inference, a bounded durable agent/workflow engine, voice workbench and a separately enrolled elevated worker. Children cannot exceed parent tool permissions; root budgets cover the complete tree. Preserve original data/auth/projects and legacy internal identities.

Golemancy inspected at `d39b6620414a022b0a0a6707b8861322ea251826` (Apache-2.0). The small accessibility snapshot formatter is adapted with attribution in `vendor/golemancy`; its backend/provider/telemetry code is not incorporated. Browser automation does not imply arbitrary native visual computer use.

## Release gate

Publish only after candidate source checks, real Windows runtime/voice/browser tests, actual packaged-dependency checks, fresh/upgrade/installer preservation, and reviewed UI captures pass. Update README/current feature list and the single changelog, plus private continuity references. A branch push cannot publish; the release job is main-only and depends on validation and desktop acceptance.

After installation, separately confirm the real GPT account, physical microphone/speakers, interactive UAC enrollment, and a daily-use workflow. CI uses synthetic identity/layout fixtures and an already-elevated disposable runner; label those limits clearly. Keep 0.12 rather than claiming v1.0 maturity from feature count.
