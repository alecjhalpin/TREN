# TREN v0.4 validation — 2026-10-12

Python 3.12.14/Linux: python -m unittest discover -s tests -v: 33 tests passed (11 app, 14 Codex, 1 upgrade/rollback, 6 web, 1 UI structure). Temporary data and mock services; fake CLI subprocess transport. New tests physically create/edit a Python file and execute it expecting 7; restart test marks queued/running/cancelling jobs interrupted. Existing tests verify running/queued cancellation, timeout, auth/path validation, reminders/memory/Gaming/web and data-preserving update/rollback.

JavaScript syntax passes node --check. node tests/ui_logic.cjs passes authorization-before-submission, project/expected paths, edit/review, chat override, dialog cancellation and render/poll smoke checks in a minimal DOM simulator. This does not verify native dialog/event behavior or layout.

Rendered Playwright checks could not run: Chromium runtime absent; download returned invalid/truncated archives. No screenshot visual QA or real Safari/mobile browser test is claimed. Expanded Windows checks remain in LOCAL-VERIFICATION.md.

Live v0.3 baseline separately user-confirmed: Plus login, Codex v0.162.1, SANDBOX_OK, successful TREN task #2 file creation/preview and local calculator execution. Real v0.4 Windows install/inference/cancellation/process cleanup/restart, live Ollama/web/Tailscale and visual layout remain unverified here.

Original v0.3 application/scripts/tests and ZIP preserved; release excludes data, pairing secrets, caches and backup snapshots. No model or installed dependency changes required on user PC.
