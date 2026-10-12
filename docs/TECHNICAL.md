# VEYRA technical guide

Current source: v0.12.0. This guide describes implemented functionality; verification scope is in [Testing](TESTING.md).

## Architecture and providers

Python 3.11+ standard-library HTTP backend on 127.0.0.1:8765, a single-file frontend, and SQLite/WAL in data/assistant.sqlite. ChatGPT supplies online conversation and PC-agent reasoning through eligible plan sharing. Ollama (default qwen3:8b) supplies local chat/fallback and scheduled routines. Codex CLI uses its separate saved ChatGPT login for project coding. No API key is configured for these ChatGPT connections.

Auto with ChatGPT preferred makes a tool-free GPT routing request using recent chat and PC-task context, selecting chat, agent, code or review. It shows a reason; manual modes override Auto. Code/review open the project permission dialog before execution. Routing costs an extra request and plan usage. With Ollama preferred, Auto uses local conversation; PC/Codex modes remain selectable. Slash commands retain their existing local paths.

Chats, saved notes, routines, device pairing, PC jobs and coding jobs are local persistent records. This development thread and ChatGPT account memory are not automatically imported into TREN. The PC must remain awake and running to perform work. The Windows listener reserves its port exclusively before initializing job state.

## Connect once

On your Windows PC, open Settings → ChatGPT conversation → Connect ChatGPT. Finish the official browser sign-in and grant TREN plan-sharing permission. The consent screen controls eligible plan usage and app limits. Successful consent makes ChatGPT the preferred conversation provider. No API key, separate API billing, Codex token reuse or private ChatGPT endpoints are configured.

Use Refresh available models to see the account's visible model catalog. The default follows server order; choose a returned model explicitly if desired. Models are discovered with the same OAuth credential used for inference. Plan eligibility and availability are account-dependent; a permission or usage-limit failure is shown clearly.

Ollama remains selectable for local chat. Optional fallback is off initially: turn it on and save preferences if you want ChatGPT failures to use Ollama. Fallback replies are labelled. Codex continues to handle coding/review with its separate existing login. Scheduled routines currently remain on Ollama.

## Continuity and capabilities

TREN sends recent chat (up to 16 messages, bounded context) and up to 30 saved notes to the selected model. Notes, reminders and chat stay in TREN's SQLite database. ChatGPT account memory and this project's development conversation do not automatically transfer. Explicit /remember and /remind still work without a model request.

ChatGPT supplies conversational text. TREN uses existing read-only web search/page tools for explicit search requests, current/latest/today requests and supplied HTTP(S) URLs, then sends bounded evidence for the response. This is a simple grounding pass: one search and one page or one supplied URL, not a model-directed web research loop. Results/failures appear in Activity. Other live lookups can use Web search or Ollama. Web access off disables these lookups; choose Ollama too for offline conversation. Regular Chat does not execute PC tasks. PC Agent has the separate capabilities below; voice and an animated orb remain planned.

Replies are saved only after a complete response. Late plan-limit errors or interrupted streams never save partial text as success. ChatGPT-labelled replies, Ollama fallback replies and local command results retain their provider labels across restart. Older chat rows are migrated as Ollama.

## Credentials and requirements

Python 3.11+; Windows; Node.js already installed for Codex (Node 22+ recommended). The Python standard library implements the documented public OAuth/Responses protocol. Node's built-in crypto verifies RS256 ID token signatures against issuer JWKS; no SDK package downloads are needed.

Tokens are encrypted with Windows DPAPI for the current Windows user and written atomically to data/chatgpt/connection.dpapi. They are never returned in browser state, URLs, command arguments or error text. Sign-in opens on the TREN PC with a short-lived loopback listener, state/nonce/PKCE checks and registered client validation. Client registration and an opaque host ID persist across attempts. Rotating refresh tokens are checkpointed before identity-key checks, so a key-service outage can recover on a later request. Disconnect removes local credentials and attempts remote revocation; if remote revocation fails, a notice asks you to disconnect TREN in ChatGPT Settings. Copying the credential file to a different Windows account will not decrypt it. The integration retains one original ChatGPT account; multiple profiles/account switching are not implemented.

The updater validates an explicit file allowlist. Current data, Codex auth and model installations remain intact. Finish/cancel ChatGPT sign-in before installing an update.


## Access and elevation

Local drives and ordinary paths are accessed under the Windows account running TREN. Permission errors, locked/protected files and Windows security boundaries still apply. Direct file tools protect TREN runtime/authentication data, its installed app files and Codex login credentials. Network/device paths are not supported by those file tools. Reviewed general commands are powerful and can perform effects beyond the dedicated file tools; review their purpose and script.

An elevated command starts a separate Python/PowerShell worker using Windows ShellExecuteEx runas. UAC is controlled by Windows and must be completed on the PC, including when the request comes from your phone. TREN never disables UAC or security policy, steals administrator credentials or elevates the HTTP server. The worker receives the approved payload, checks its digest, monitors the originating process identity/cancellation, and returns an authenticated result. Decline/failure/uncertain termination is reported rather than success. Full elevation can still be denied by Windows/account policy.

## Tool loop and verification

GPT uses documented namespace function calls on the same plan-sharing connection. Completed Responses output and encrypted reasoning items are carried into subsequent input, paired with call_id tool results; no stored remote conversation or API-key fallback is used. Evidence from files/commands/web pages goes to GPT and is treated as untrusted data. Common credential patterns are redacted, but this is not a guarantee that arbitrary private content contains no sensitive information. Use Off or read-only mode as appropriate.

Only known tools and validated arguments execute. Approval is one-time, bound to a random request ID and an action digest, and expires after 15 minutes. Denial stops the task. Cancellation stops ordinary command process trees where possible, does not undo completed actions, and cannot guarantee detached apps stop. Elevated workers also monitor parent lifetime; unconfirmed elevated results require inspection before retrying.

File-tool replacement/move/delete backs up ordinary files up to 64 MiB under data/pc_backups with original-path metadata. File-tool writes/copies/moves verify resulting content. Directory deletion, binary reads and larger operations can use reviewed scripts. General PowerShell scripts, app launches and external actions have no automatic backup/rollback. Commands have 1–600 second timeouts and bounded captured output; file search is bounded. Tasks have model/tool/context/time budgets and do not auto-replay after restart. Failed or interrupted jobs may have completed earlier steps; inspect their action logs before retrying. A second TREN instance reserves the listening port before touching jobs.

Native visual computer-use is unsupported on this plan-sharing route. This release does not add a visual browser driver, logged-in browser sessions, screenshot interpretation, reliable click automation, desktop wrapper, native phone app or voice. Reviewed scripts can use installed programmatic Windows/app interfaces, but TREN must not pretend it sees a screen. Ollama retains chat/routines; the PC agent is GPT-only and does not silently retry actions through another model.


## Codex projects and permissions

Projects are named directories under data/projects; names use letters, numbers, underscores and hyphens. Requests open the task review dialog with project, read-only or workspace-write permissions, expected relative output paths and a 1–60 minute limit. Review the proposed settings before starting. Missing expected artifacts are failures rather than invented success. File previews are bounded. The CLI finishing does not establish that generated code is correct.

One coding worker processes the durable queue. Gaming mode holds queued coding work and future scheduled runs; active work continues until completed or cancelled. Cancellation stops the ordinary process tree but does not undo written files. Restart marks interrupted jobs rather than replaying them. Use Continue this project for a follow-up. Include relevant saved-note requirements in coding prompts; those notes are not automatically sent to Codex.

Codex runs shell-free with explicit read-only/workspace-write sandbox and escalation denied. Windows npm shims resolve to their installed Node entry. Existing CLI configuration/project instructions/MCP capabilities can affect behavior; the write boundary is not a complete private-file confidentiality boundary. TREN does not bypass sandbox setup or read Codex credential files. API-key environment variables are removed from the child process.

## Device sessions and message composer

Remembered devices persist for 90 days unless expired, revoked, logged out or their cookie is removed. SQLite stores hashed bearer credentials; cookies are HttpOnly/SameSiteStrict and Secure over HTTPS. PC and phone addresses use separate cookies and pairing. Temporary pairing ends at process restart. Settings lists/revokes devices.

Enter sends, Shift+Enter inserts a newline, and composition/repeated key events do not submit. Messages clear on submission, preserve newer drafts, and restore failed drafts. Coding requests retain the permission dialog. Assistant content uses safe text/DOM rendering for bold, headings, lists, HTTP(S) links and code; raw assistant HTML is not interpreted.

## Release process

Canonical public repository: alecjhalpin/Veyra. The release workflow publishes new stable versions from main after build/test validation. Current version is in version.json. Change it to a newer three-part version for a release; an already-published version is skipped and its assets remain unchanged.

The published asset is TREN-vX.Y.Z.zip with an internal checksum manifest. GitHub adds an asset SHA-256 digest, which the in-app downloader verifies. GitHub-generated source archives cannot be installed as updates. No GitHub token is stored by TREN; Actions uses the repository token with contents:write.

The updater accepts public stable releases, newer versions, bounded ZIPs and allowlisted paths. It preserves current data/configuration and backs up code before restart. See the update limits below. Hashes detect corruption under the selected trusted source; no independent publisher signature is implemented.

## Update limits and recovery

Release validation bounds ZIP size to 16 MiB, expanded size to 64 MiB and entries to 300, checks manifests/hashes/version/paths, and rejects unexpected files. Source-only docs/ pages stay in GitHub and are not included by the runtime release allowlist; README links to their GitHub pages. Adding runtime files requires a compatible updater path.

Install/restart requires explicit confirmation and blocks active work. The trusted current updater supervisor waits for shutdown, backs up code and snapshots SQLite, installs validated files, relaunches and checks the versioned HTTP server response. Failed startup attempts restore previous code and relaunch. Settings can restore the previous in-app update; bootstrap upgrade prints its rollback command. Ordinary rollback preserves current data, pairing, hosts and projects. Database snapshots and restart logs are private and may contain pairing information; keep them local.

Old installations need the one-time upgrade.bat bootstrap described in the main README. Never rerun setup merely to update an installation. Desktop packaging, local voice/orb and Playwright browser tools are implemented in v0.12. Phone and arbitrary native visual desktop control remain future work.

## References

- [ChatGPT sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Plan-sharing limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Codex noninteractive use](https://developers.openai.com/codex/noninteractive)
- [Codex on Windows](https://developers.openai.com/codex/windows)

## Desktop companion

The Electron companion runs the existing installation through its saved folder selection, using a sandboxed, isolated renderer and native tray/menus. It has a narrow origin-validated preload bridge for theme/menu and optional setup, without renderer Node access. A random in-memory native controller credential is passed to the owned backend through its environment; control requests are loopback-only and require the exact credential, confirmation and host/origin checks. The status endpoint returns only version, installation fingerprint and controller hash, not paths or credentials. Backend updater children inherit the controller environment so native Quit can still address the current owned backend after a backend update. See [Desktop setup](DESKTOP.md).

Assistant profile names and setup completion are SQLite settings. Existing users migrate without forced onboarding. Backend mode/inference functions use the saved assistant identity, while application/update/package identities stay unchanged pending rebranding. Bundled managed runtime directories are versioned and staged separately from code updates; optional tools remain local and separate from the backend code manifest.

## Brand transition — v0.11.0

Public product name: VEYRA (formerly TREN). Assistant identity is stored separately in SQLite. New fallback name: Nova; completed returning profiles without a saved name are assigned their historic TREN name using INSERT OR IGNORE. Saved custom names are never replaced. Backend desktop application identifier remains TREN for compatibility; public OAuth consent hints/sign-in text use VEYRA. Legacy internal environment variables, controller headers, appId/package/executable identities and stored profiles remain compatible. The public repository is alecjhalpin/Veyra; current backend release assets use VEYRA-vVERSION.zip. Frontend welcome art is embedded so older strict release allowlists still receive it without new backend asset routes. Desktop icon and GitHub hero assets live in the repository; desktop packaging includes its icon.

## Integrated agent runtime

`agent_runtime.py` adds agent/workflow/message/memory/job tables to the existing SQLite database. Each agent has an independent context and workspace; enabled whole-PC tools are not OS-sandboxed. Root tasks share call, runtime, context, agent-count, concurrency and depth limits. A runtime watchdog cancels blocked provider requests; tool/process cancellation checks the same shared state. Model-reported usage is shown separately from unavailable plan quota information.

The private NDJSON Node worker pools dedicated Playwright profiles and stdio/streamable-HTTP MCP connections. MCP credentials stay protected on the current Windows account. Native OAuth MCP authorization is not implemented; configure trusted commands or HTTP headers explicitly. Browser/file/MCP content is untrusted evidence. Local Whisper/Kokoro models are cached under data; voice never needs a paid voice API.

Cron workflows use local time or UTC, coalesce missed runs and avoid overlap. A failed/uncertain previous run pauses its schedule for inspection. Restart marks incomplete jobs interrupted, without replay. Continuing a checkpoint records prior descendant effects and blocks exact mutation replay. Arbitrary shell effects are not automatically undoable; file-tool backups and updater rollback have narrower verified guarantees.

Automatic PC mode requires explicit warning/confirmation; a separately enrolled per-user Highest interactive Task Scheduler worker handles approved unattended administrator requests after one-time UAC. Requests/results are authenticated, expire, and remain tied to the requesting process identity. Stop All pauses new execution/schedules and cancels providers, tools and owned subprocesses. Windows must remain awake and signed in.

Portable backups include agents, memory, workflows, budgets and selected settings. Credentials, browser sessions and elevation keys are excluded. Restore leaves execution paused, schedules disabled and access in review; reconnect MCP separately. The complete desktop updater has a built-in release source; backend manifests/backups preserve data during startup migration.

## Dependency maintenance

Pinned runtime: Playwright 1.64.0, Transformers.js 3.8.1, Kokoro.js 1.2.1, sharp override 0.35.5. Models use local CPU inference. npm scripts are disabled when staging these runtime dependencies. The current audit reports six moderate transitive entries through sprintf-js 1.1.3 → roarr/global-agent → the ONNX postinstall helper; the helper is not called by the inference worker and its install script is disabled. There is no patched sprintf-js release available at this checkpoint. Do not apply npm audit --force major upgrades without testing model/runtime compatibility. Preserve dependency licenses and Golemancy attribution in packaged resources.


Windows desktop packages include signature-verified Microsoft app-local C++ runtime DLLs beside private Node and ONNX, with provenance and redistribution notices. End users do not need the build host's PowerShell 7 or Visual Studio installation. Both speech preview and recognition place model caches under preserved data/voice_models. Editing the default agent name also updates the saved assistant identity.
