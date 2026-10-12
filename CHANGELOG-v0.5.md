# v0.5

- Authenticated Settings updates: ZIP preparation, public GitHub latest-release/digest check, download, explicit install/restart and prior-update restore.
- Trusted local restart supervisor, busy-work guard, code backups/database snapshots, checksum/path/size validation and rollback on startup failure.
- One-time bootstrap auto-detects standard installation or uses folder picker; future update ZIPs stay inside TREN.
- Manifest release builder and GitHub release preparation instructions.
- Preserved data, pairing secret, model dependencies, provider behavior and existing UI; sessions still reset on restart.
- Recorded user-confirmed v0.4 edits/output 7, cancellation, queued restart recovery, chat, memory and reminders.

## v0.5.1

- Connected clean source/release workflow to alecjhalpin/TREN. Default release source uses that repository when no user preference is saved.
- Main-push/manual release workflow validates and tests packages, then publishes new versions without overwriting existing assets.
