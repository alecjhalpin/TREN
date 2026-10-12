# v0.7.0

- Added persistent, individually revocable 90-day device pairing with hashed session credentials and an explicit temporary-session option.
- Added named remembered-device controls in Settings; logout revokes the current saved credential.
- Fixed composer timing: clear on submission, keep newer drafts, restore failed messages, preserve accepted-message state if refresh fails.
- Hardened Enter handling for Shift, composition and repeat; coding authorization behavior preserved.
- Replaced the current-release README feature list as requested; no dependency reinstall, GPT re-consent or model download required.
- Automated persistence/auth/composer checks and regression suites run before publication; live Windows/browser acceptance is separate.
