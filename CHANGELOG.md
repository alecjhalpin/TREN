# Changelog

## Unreleased — integrated mega-update (in development)

Source now includes scoped agents and SQLite memory, cron workflows, shared recursion budgets, review/automatic permission handling, durable task evidence and recovery, pooled MCP and Playwright tools, local Whisper/Kokoro voice with an orb, workspace preview, portable backup/restore, an optional elevated worker and a unified desktop update path. These features are undergoing integrated acceptance; they are not a published release.

Verified locally: 95 ordinary automated tests pass, plus the real speech generation/transcription round trip. Windows Edge, packaged UI/microphone, unattended program installation and installer upgrade checks are being run on the development branch. See `docs/DEVELOPMENT.md` for the acceptance matrix and limitations.

## 0.11.1 — 2026-10-12

Separate VEYRA installer folder branding from the retained legacy executable/appId/profile. Add an installation-folder/desktop-shortcut options page and VEYRA shortcut names, retain desktop-shortcut choice on silent updates, and update matching login-launch registry entries when the legacy program folder changes. Use renamed alecjhalpin/Veyra release repository; migrate only the exact old backend default. User confirmed the harmless elevated administrator/UAC diagnostic worked. Installer build and fresh/upgrade acceptance are verified separately.

## 0.11.0 — 2026-10-12

Rebrand the public application to VEYRA with the tagline “Your AI. Your computer. Your rules.” Add approved hero artwork, a transparent simplified V desktop icon, blue theme accents and branded Windows installer/menu/tray/welcome flow. New unnamed assistants use Nova; returning unnamed assistants retain TREN and explicit names are preserved. Keep legacy package/app/update identifiers, executable name, desktop profiles, storage paths and backend ZIP names compatible. New OAuth consent displays VEYRA; existing protected credentials are retained. Automated and Windows release acceptance is recorded in docs/TESTING.md separately from user acceptance.

## 0.10.0 — 2026-10-12

First-install backend plus hash-verified private Python/Node runtimes; optional Codex/Ollama installers with explicit native confirmation and reuse checks. First-run assistant naming/ChatGPT/optional-tools onboarding, persisted assistant identity, returning-user migration, themed desktop title bar with a narrow validated preload bridge, and readable custom mode menu. Existing backend data/updater paths preserved. TREN remains the application brand pending user choice; DeepSeek/Grok/Claude remain planned. Fresh Windows/runtime/visual acceptance is distinct from synthetic tests.

## 0.9.0 — 2026-10-12

Windows Electron desktop companion with existing-folder selection, hidden Python startup, dedicated conversation window, tray lifecycle, opt-in login launch, single desktop instance and explicit shell-update controls. Adds saved light/dark/system appearance to browser and desktop. Local backend controller requires a random desktop-only credential; the renderer cannot access it. Existing pairing, GPT/Codex/Ollama, data and backend updater remain in place. Windows packaging and live acceptance are distinct from fixtures.

One release history for TREN. Older source snapshots remain in Git tags and Releases.

## 0.8.4 — 2026-10-12

Replace Auto's unconditional PC-job routing with GPT semantic classification into chat/agent/code/review. Show mode and recommendation reason, respect explicit manual choices, validate model decisions, and preserve Codex review and action approval controls. Routing has no tools and cannot execute actions. Adds an extra GPT request; live routing quality remains pending. Ollama-preferred Auto continues local chat.

## 0.8.3 — 2026-10-12

User verified correct live PC drive-storage result in v0.8.2. PC results now use conversation bubbles/replies instead of task cards, with collapsed action evidence and visible approvals/failures. Safe DOM rendering supports bold, code, headings, lists and HTTP(S) links. No raw assistant HTML is interpreted. Visual acceptance remains pending.

## 0.8.2 — 2026-10-12

Retain response.output_item.done items when response.completed omits/repeats no output; preserve completed encrypted reasoning and tool calls, with successful terminal completion still required. Clearer Auto label and normal ChatGPT label for completed responses without actions. User verified ordinary Auto greeting works but storage query returned an empty completed response in v0.8.1. Parser defect is verified against synthetic fixtures; attribution of the user's failure and live Windows acceptance remain pending.

## 0.8.1 — 2026-10-12

Windows exclusive HTTP port reservation; explicit ChatGPT option uses plain conversation; more specific tool-response failure messages. User confirmed v0.8 update succeeds after closing duplicate processes and ordinary chat works. PC storage request failed; live tool acceptance remains pending. Repository documentation consolidation is planned, not completed.

## 0.8.0

- Added general GPT namespace tool calling with serial results/continuation and a durable PC-task/action log.
- Added live storage/system checks, broad ordinary-path file inspection and reviewed mutations, app/URL launch, general PowerShell execution and task-specific Windows UAC elevation.
- Added one-time action-bound approvals, denial, cancellation, read-only/off modes, no-replay restart handling and no automatic model failover after side effects.
- Added file-tool backup/content verification, output/time/step budgets, authenticated elevated results and parent-lifetime cancellation.
- Prevented second-instance startup from marking the first instance’s jobs interrupted.
- Preserved existing GPT chat, Codex coding, Ollama routines, device pairing and update paths. Current-release README feature list replaced.
- Source/fixture-tested functionality is separate from pending real Windows/plan-tool/UAC acceptance. No native visual computer-use, desktop app or voice claim.

## 0.7.0

- Added persistent, individually revocable 90-day device pairing with hashed session credentials and an explicit temporary-session option.
- Added named remembered-device controls in Settings; logout revokes the current saved credential.
- Fixed composer timing: clear on submission, keep newer drafts, restore failed messages, preserve accepted-message state if refresh fails.
- Hardened Enter handling for Shift, composition and repeat; coding authorization behavior preserved.
- Replaced the current-release README feature list as requested; no dependency reinstall, GPT re-consent or model download required.
- Automated persistence/auth/composer checks and regression suites run before publication; live Windows/browser acceptance is separate.

## 0.6.0

- Added documented ChatGPT plan-sharing OAuth consent, Windows-protected credential storage, refresh recovery and account model discovery.
- Added GPT conversation with recent TREN history/saved notes; preferred provider becomes ChatGPT after successful sharing consent.
- Added explicit local provider choice and opt-in, labelled Ollama fallback. Coding remains Codex; routines remain Ollama.
- Added Settings controls, safe connection state and persistent reply provider labels with backwards-compatible SQLite migration.
- Added bounded existing-web-tool evidence for explicit/current requests and supplied URLs.
- Preserved previous coding/update functionality and compatible release filenames. No dependency reinstalls or model redownloads.
- Automated protocol/UI/backend checks are distinct from pending Windows live consent, DPAPI and real model verification.

## 0.5

- Authenticated Settings updates: ZIP preparation, public GitHub latest-release/digest check, download, explicit install/restart and prior-update restore.
- Trusted local restart supervisor, busy-work guard, code backups/database snapshots, checksum/path/size validation and rollback on startup failure.
- One-time bootstrap auto-detects standard installation or uses folder picker; future update ZIPs stay inside TREN.
- Manifest release builder and GitHub release preparation instructions.
- Preserved data, pairing secret, model dependencies, provider behavior and existing UI; sessions still reset on restart.
- Recorded user-confirmed v0.4 edits/output 7, cancellation, queued restart recovery, chat, memory and reminders.

## v0.5.1

- Connected clean source/release workflow to alecjhalpin/TREN. Default release source uses that repository when no user preference is saved.
- Main-push/manual release workflow validates and tests packages, then publishes new versions without overwriting existing assets.

## 0.4

- Conversation-first layout, Tools and Settings; existing controls retained.
- Auto/Chat/Build/Review composer, compact explicit coding permission dialog and advanced options.
- Inline progress, cancellation, file previews and project continuation; browser last-project preference.
- Enter/Shift+Enter and Gaming hold explanation.
- Expected paths supplied to Codex prompt; sandbox/auth/enforcement unchanged.
- Incremental code/docs update and rollback with v0.4 backup naming.
- Follow-up file edit/execution and active restart tests; browser interaction verification.

## 0.3

- Added a Codex coding provider using installed CLI, existing ChatGPT login, stdin prompts and JSONL events.
- Added durable bounded single-worker queue, timeouts, cancellation, restart recovery, task history and file existence verification.
- Added project directory validation, read-only default, explicit project-write confirmation, shell-free Windows npm resolution and output redaction.
- Added Coding UI, common coding-intent handoff from chat, provider toggle and authenticated file previews.
- Preserved Ollama, corrected v0.2.1 webtools.py, memory, reminders, activity, pairing, host/origin protections and gaming behavior.
- Added code-only upgrade with backup and rollback. No dependency reinstall, personal data or credentials in distribution.
- Deferred full PWA and voice to keep this milestone focused. Phone access continues through private Tailscale Serve.

## Documentation consolidation — 2026-10-12

Merged version-specific READMEs, changelogs and test reports into current documentation. User confirmed v0.8.4 Auto routing works. No runtime changes or new release version.
