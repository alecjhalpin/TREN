# TREN v0.5 validation

Python 3.12.14/Linux: 45 tests passed: 13 app, 14 Codex, 1 UI structure, 10 updater, 1 bootstrap upgrade/rollback, 6 web. Final suite passed after regenerating the manifest. Services use fixtures/fake Codex. Tests cover updater authentication and explicit confirmation, busy-work maintenance cleanup, stage/manifest/hash/version/URL/repository validation, duplicate/traversal/link/unknown file rejection, preserving DB/pairing/hosts, transaction failure rollback, failed-health rollback, trusted-helper copying and existing app regressions.

Separate real-process Linux end-to-end test passed: start TREN, authenticated HTTP ZIP upload, explicit install, original process exit, detached new-version startup, same pairing secret and preserved memory/hosts, in-app rollback and old-server restart. No AI/model/network calls. This does not verify Windows process flags or UAC behavior.

JavaScript syntax and DOM-simulator UI logic pass, including update check/upload/explicit-install handlers. Browser rendered/native event QA unavailable in build environment; no layout claim. Public GitHub release/download behavior fixture-tested, not a live TREN GitHub release (repository not created). Windows bootstrap auto-detection/folder picker, detached update restart and browser reconnect still need local verification.

v0.4 Windows reliability is separately user-confirmed: edits/output 7, cancellation, queued restart recovery, ordinary chat, explicit memory and reminders. v0.3/v0.4 source/release preserved. No user data, credentials, logs, caches, backup snapshots or allowed-hosts customization in packages.
