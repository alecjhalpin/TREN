# Test results — TREN v0.3

Environment: Python 3.11, Linux development container. Tests use temporary databases and project directories, not uploaded personal data.

Command: `python -m unittest discover -s tests -v`

Release result: 30 tests passed (17 application HTTP/regression + 12 Codex + 1 upgrade/rollback).

Additional checks: frontend JavaScript syntax checked with Node; Python modules compile successfully; release archive inspected to exclude data, pairing codes, credentials and caches.

Existing regression suite: HTTP startup/authentication, host/origin checks, pairing rate limits, Ollama payload compatibility using mocked responses, explicit memories, reminders and recurring catch-up, gaming pause, tool loop/budget, web-search parser/error behavior, SSRF/private-address restrictions, redirects, public IP pinning and page text cleanup.

Codex tests: real subprocess transport against a **fake CLI** (not a real OpenAI session), JSONL success, physical output file verification, nonzero failure, error-event failure with zero exit code, missing expected file, timeout via controlled clock, process cancellation, queue cancellation, restart recovery, invalid names/paths, write confirmation, symlink rejection, common secret redaction, API key exclusion, missing CLI/auth timeout/wrong auth, Windows npm entry resolution with simulated paths, and gaming hold. Authenticated HTTP endpoint tests cover submission, cancellation, file previews/path rejection, provider disabling and unauthenticated rejection.

Upgrade tests: temporary installation, existing database byte preservation, pairing-code preservation, allowed-hosts preservation, code replacement and rollback. No Windows batch execution is claimed.

Not live-tested: your Windows PC, installed Codex version, real ChatGPT authentication/inference/usage limits, Windows process-tree termination and sandbox initialization, live Ollama inference, live DuckDuckGo network service, Tailscale, iPhone microphone or native voice. Follow README-v0.3.md first-task procedure for the actual local integration check.
