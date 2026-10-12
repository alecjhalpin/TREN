# Integrated release development

Approved 2026-10-12. Build one integrated mega-update; do not publish partial feature releases. Published v0.11.1 remains the baseline until full acceptance passes. Phone capability is outside this release.

## Acceptance matrix

| Area | Required outcome | Status |
| --- | --- | --- |
| Permissions | Whole-PC automatic actions require warned explicit opt-in; review/inspect/off remain; immediate revocation | Pending |
| Elevated worker | Separate one-time UAC setup, authenticated requests, disable/stop; no system-wide UAC disabling | Pending |
| Scheduling | Cron and reusable workflows, restart/coalescing, no overlapping/replayed mutations | Pending |
| Memory | Agent-scoped SQLite CRUD, pinned context, priority/recency, no context leakage | Pending |
| MCP | Stdio/HTTP initialization, pooled lifecycle, timeout/cancel, tools schemas, explicit connections | Pending |
| Browser | Playwright isolated profiles, navigation/click/fill/extraction/download/upload, cancellation | Pending |
| Agents | Isolated missions/workspaces, sub-agent recursion under shared budgets, live durable task evidence | Pending |
| Workspace | File listing/preview/reference, actual path verification | Pending |
| Voice/orb | Click mic, local transcription, spoken response, interruption/mute, device selection/calibration | Pending |
| Activity | Task inbox, notifications, stop-all, runtime/tool/concurrency/depth limits | Pending |
| Recovery | Checkpoints, inspect partial actions, never replay side effects silently | Pending |
| Backup | Export/restore settings, workflows, memory; preserve private credentials in place | Pending |
| Updates | Built-in repository, one download action and restart confirmation; full-package migration | Pending |
| Install task | Official small app and dependencies, verified execution, unattended elevation, failure/cancel | Pending |

## Source review

Golemancy inspected at d39b6620414a022b0a0a6707b8861322ea251826 (Apache-2.0). Browser driver wraps agent-browser/Playwright; MCP pooling fingerprints full configuration and permissions; agent-scoped memory is pinned then priority/recency ranked. OS computer-use is not inferred from these browser tools. Any copied utility keeps license and attribution; no private OAuth/backend routes, upstream telemetry or API-key voice flow is adopted.

## Architecture

Keep Python/SQLite core and official GPT plan-sharing. Add a bounded multi-agent/workflow engine, a pooled Node tool worker (Playwright/MCP/local Whisper), voice UI with Windows speech synthesis, and an explicitly installed elevated worker for unattended admin commands. Desktop packaging supplies dependency setup and coordinated backend upgrade. Separate agent contexts and browser profiles; inherited tool permissions cannot exceed a parent's; shared root budgets cover recursive children. Model-reported usage is distinguished from unavailable quota information.
