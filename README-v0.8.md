# TREN v0.8.0 — general PC agent

Update through Settings → Updates → Check → Download → Install & restart. Your remembered pairing, GPT consent, chats, notes, Codex login and Ollama models are preserved. No new package installs are required.

## Use it

Keep ChatGPT as the preferred provider. With PC agent enabled, Auto uses the agent for ordinary GPT requests; project-coding detection still opens the existing Codex permission dialog. Choose PC agent explicitly for PC work, or Chat for conversation without PC tools. /remember and /remind still use existing explicit commands.

Examples:
- How much free storage do I have on each drive?
- Find PDF files in my Downloads folder and show their sizes.
- Create a folder on my Desktop and put a notes file inside it.
- Open this folder/application on my PC.
- Run a finite system diagnostic through PowerShell and explain its output.
- Perform an administrator task (only after reviewing the proposed command and Windows UAC).

Settings → PC agent offers broad PC access with action review, read-only inspection, or Off. Changing access cancels an active task. One PC task runs at a time; ordinary Chat remains available. Read-only file/drive checks run automatically. Every PowerShell script, app launch and file mutation needs action review in TREN. This provides broad capabilities without registering a separate feature for each new task; it does not mean unrestricted unattended command execution.

## Access and elevation

Local drives and ordinary paths are accessed under the Windows account running TREN. Permission errors, locked/protected files and Windows security boundaries still apply. Direct file tools protect TREN runtime/authentication data, its installed app files and Codex login credentials. Network/device paths are not supported by those file tools. Reviewed general commands are powerful and can perform effects beyond the dedicated file tools; review their purpose and script.

An elevated command starts a separate Python/PowerShell worker using Windows ShellExecuteEx runas. UAC is controlled by Windows and must be completed on the PC, including when the request comes from your phone. TREN never disables UAC or security policy, steals administrator credentials or elevates the HTTP server. The worker receives the approved payload, checks its digest, monitors the originating process identity/cancellation, and returns an authenticated result. Decline/failure/uncertain termination is reported rather than success. Full elevation can still be denied by Windows/account policy.

## Tool loop and verification

GPT uses documented namespace function calls on the same plan-sharing connection. Completed Responses output and encrypted reasoning items are carried into subsequent input, paired with call_id tool results; no stored remote conversation or API-key fallback is used. Evidence from files/commands/web pages goes to GPT and is treated as untrusted data. Common credential patterns are redacted, but this is not a guarantee that arbitrary private content contains no sensitive information. Use Off or read-only mode as appropriate.

Only known tools and validated arguments execute. Approval is one-time, bound to a random request ID and an action digest, and expires after 15 minutes. Denial stops the task. Cancellation stops ordinary command process trees where possible, does not undo completed actions, and cannot guarantee detached apps stop. Elevated workers also monitor parent lifetime; unconfirmed elevated results require inspection before retrying.

File-tool replacement/move/delete backs up ordinary files up to 64 MiB under data/pc_backups with original-path metadata. File-tool writes/copies/moves verify resulting content. Directory deletion, binary reads and larger operations can use reviewed scripts. General PowerShell scripts, app launches and external actions have no automatic backup/rollback. Commands have 1–600 second timeouts and bounded captured output; file search is bounded. Tasks have model/tool/context/time budgets and do not auto-replay after restart. Failed or interrupted jobs may have completed earlier steps; inspect their action logs before retrying. A second TREN instance reserves the listening port before touching jobs.

Native visual computer-use is unsupported on this plan-sharing route. This release does not add a visual browser driver, logged-in browser sessions, screenshot interpretation, reliable click automation, desktop wrapper, native phone app or voice. Reviewed scripts can use installed programmatic Windows/app interfaces, but TREN must not pretend it sees a screen. Ollama retains chat/routines; the PC agent is GPT-only and does not silently retry actions through another model.

## Verification status

Automated tests cover real storage reads on Linux, temporary file operations/backups, a simulated GPT tool loop, exact/stale/repeated approval handling, denial/cancellation, read-only enforcement, partial-provider failures, restart interruption, paired API routes and UI routing. Harmless real subprocess fixtures cover exit/output/timeout/cancellation. UAC payload/result integrity uses fixtures; actual Windows PowerShell/UAC, live model namespace calls, rendered browser/phone behavior and Windows PC tasks remain pending user acceptance. Existing v0.7 pairing/composer and v0.6 GPT basic operation are user-confirmed.

Protocol references:
- https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations
- https://developers.openai.com/api/docs/guides/function-calling
- https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecuteexw
