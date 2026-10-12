# TREN Local v0.3

## Upgrade your working v0.2.1 installation

1. Stop TREN with Ctrl+C in its existing window. Close any other TREN instance.
2. Extract this ZIP to a **new folder**, for example Downloads\Tren-v0.3-Update. Do not extract it over your installed folder.
3. Double-click **upgrade.bat** in the new folder. Paste the path to your existing Tren-Local folder (the one containing app.py and data). Press Enter.
4. The installer backs up old code and snapshots the database, then copies only the listed application files. It does not change data, pairing codes, allowed-hosts.txt, models, or installed software.
5. Start **start.bat in your existing installed folder**. Refresh the browser. Pair with the same code if asked; browser sessions reset at restart.
6. Select **Coding · Codex → Check Codex**. Expected: **ChatGPT login ready**.

No pip/npm installs, model downloads, API keys, or additional subscriptions are required by this upgrade. Do not run the old setup.bat for this update. The original setup files remain included for reference only.

## First local integration test

- Leave Gaming mode off. Set coding backend to Codex.
- Project: `calculator-check`. Request: `Create calculator.py that prints 2 + 2. Do not install dependencies.`
- Select **Allow project edits**, enter `calculator.py` under expected output files, queue, and accept the confirmation.
- Watch status change queued → running → completed. Expand Progress and result.
- Click **Preview calculator.py**. Independently inspect the actual file in `data\projects\calculator-check` in your installed TREN directory.
- Optionally run `py -3 calculator.py` from that project folder after inspecting it. Expected output: 4.
- Only this local procedure verifies the real CLI, your authentication, Windows sandbox, and account limits. Packaged tests use a simulator.

## Projects, providers, and background work

Coding uses the installed Codex CLI and its saved ChatGPT login; ordinary chat, web research, memories, and reminders continue using Ollama. Coding backend can be disabled in the Coding tab. Future providers can be registered in providers.py without changing memory or reminder storage.

Chat detects common coding requests and `/code ...`, pre-fills Coding, and waits for your permission choice. You can always type a request directly in Coding. This conservative detection is a convenience, not a general intent model.

Each named project is a separate directory under data/projects. Names use letters, numbers, underscores and hyphens. To work on an existing project, copy it into a named directory there first. Absolute external project directories are deliberately not supported in this release. You may copy reviewed results back afterward. Expected file paths are relative, such as `src/main.py`; missing expected files cause `artifact_missing` rather than a success claim. Verified changed/expected files have text previews up to 1 MB. Completed means the CLI completed successfully, not that every generated program is correct.

One coding task runs at a time, with at most 10 active/queued tasks. Progress refreshes with the existing state polling. Time limits are 1–60 minutes in the UI. Cancellation kills the process tree; already-written files remain. Restart marks pending/active tasks interrupted and does not automatically replay them. Resubmit intentionally. Gaming mode pauses queued coding tasks and existing scheduled reminders; active tasks continue until cancelled or finished. No keyboard/mouse automation is used.

Memory and conversation history remain shared between devices. Codex coding task history is stored in the same database but is separate from Ollama conversation history. Saved notes are not automatically sent to Codex; include relevant requirements in your coding request. Closing TREN or sleeping/offlining the PC stops work.

## Permissions and credentials

Read-only is the default. All project-write tasks require explicit confirmation, including possible changes/deletions inside that project. Back up valuable project files first. Codex runs with an explicit read-only or workspace-write sandbox and `-a never`: requests needing escalation are denied, not approved or bypassed. TREN never enables danger-full-access or a bypass flag. Network/deployment-dependent actions may fail; no unrestricted retry occurs.

The workspace-write sandbox is a write boundary, not a complete private-files confidentiality boundary. It can allow reads outside the working directory depending on OS/CLI configuration. Run only trusted tasks/projects, and avoid putting secrets in projects or prompts. Project instructions and your existing CLI configuration can affect Codex behavior. Existing configured MCP tools may grant external capabilities; review them in Codex before using unattended tasks. TREN does not alter your CLI configuration or implement a full tool-by-tool approval broker. Publishing, purchasing and deployments are excluded from the task instructions, but instructions are not an OS security boundary. Use read-only when unsure.

TREN does not read auth.json or browser tokens and does not copy credentials. It checks `codex login status` and requires ChatGPT login. API key environment variables are removed from child processes to avoid accidental API billing. Output is redacted for common bearer/API/token/password patterns and bounded to 64 KB; redaction cannot guarantee detection of every possible secret. Do not request secret output. Authentication failures, usage limits, CLI failures and sandbox denial are displayed without automatic retries. No balance/remaining quota estimate is invented.

Windows npm shims are resolved to their installed JS entry and invoked with node, shell=False. Terminal windows are hidden and cancellation uses taskkill /T. Windows sandbox setup/version differences still require local verification; initialize the sandbox through the normal Codex CLI if it reports a setup requirement. TREN will not silently weaken it.

## Rollback

Stop TREN. Each update prints a rollback command. From the extracted update folder, run:

`py -3 upgrade.py --rollback "C:\path\to\Tren-Local\backups\pre-v0.3-TIMESTAMP"`

Old code is restored and new code files removed. Current data and allowed hosts remain untouched. The extra coding_jobs table is harmless to v0.2.1. Backup folders contain a private database snapshot: keep them local and never share them. If you need database recovery, stop TREN and make a separate copy of current data before manually restoring the snapshot; ordinary rollback does not reset your memories/history. The migration creates one new table and leaves all existing schemas/rows intact.

## Windows, phone and voice roadmap / limitations

Use the existing PHONE-SETUP.md: Tailscale Serve proxies the loopback backend privately over HTTPS. Retain exact allowed-hosts entries and pairing authentication. Do not port-forward TREN or use Tailscale Funnel. Safari on iPhone can bookmark/Add to Home Screen the responsive UI; Windows can install it as a browser app where supported. This release is not an offline PWA: no service-worker cache, manifest, or push notifications were added, to avoid caching private responses and distracting from coding reliability.

Next milestones: an app manifest and icons with network-only authenticated data; an approval-capable Codex app-server adapter for granular tool confirmation; reviewed project import/export and diff previews; optional local faster-whisper transcription plus local Piper/system TTS; iPhone HTTPS push-to-talk with server-local transcription and shared history. Browser speech recognition support/privacy varies, and Safari support must be verified before offering it. Local audio engines may require new downloads and hardware tuning. Native ChatGPT voice is not integrated. No paid voice API or browser token workaround is included.

## Official references checked for this build

- https://developers.openai.com/codex/noninteractive — exec, JSONL, sandbox modes, saved CLI authentication.
- https://developers.openai.com/codex/cli/reference — command flags and working directory.
- https://developers.openai.com/codex/windows — Windows sandbox behavior.

See TEST-RESULTS.md for verified scope and CHANGELOG-v0.3.md for changes. Run tests with `py -3 -m unittest discover -s tests -v` in the extracted update folder.
