# TREN v0.7.0 — remembered devices and composer fixes

Install through Settings → Updates → Check → Download → Install & restart. Pair once after this update with **Remember this device for 90 days** checked and a device name. Existing v0.6 browser sessions were temporary; they cannot be recovered from a stopped process. Subsequent restarts/updates keep remembered pairing until its 90-day expiry, revocation, logout or browser-cookie deletion. Use the same browser and TREN address; PC loopback and phone HTTPS addresses have separate cookies. No dependency reinstall is needed.

Settings → Remembered devices lists names, pairing/expiry times and the current browser. Revoke an individual device to require its pairing code again. Disconnect this device revokes its own saved credential. Unchecking Remember this device uses a temporary browser session that ends when TREN restarts. Pair the phone separately over the existing private Tailscale HTTPS connection; this release does not implement iPhone packaging.

Session credentials are random 256-bit bearer tokens. SQLite stores SHA-256 token hashes with expiry, never raw tokens; device lists return neither hashes nor tokens. Cookies remain HttpOnly and SameSite=Strict, with Secure on HTTPS. Host/origin checks, pairing rate limits and authentication for device management remain enforced. Missing/expired/revoked credentials require pairing again. No unauthenticated convenience bypass is added.

## Composer

Enter sends; Shift+Enter adds a line. IME composition and held/repeated Enter are ignored for sending. The composer clears immediately when a chat request is submitted, and pending chat is displayed in the conversation. A new draft typed while waiting is preserved when the reply arrives. If sending fails before an acknowledged response, the old message is restored; if a newer draft exists, it is kept below the restored message for editing. A refresh failure after acknowledged delivery does not restore the delivered message. Coding requests still open their permission dialog and clear after successful task submission; cancellation preserves their request.

## Verification

Automated backend checks cover remembered-session persistence across simulated process-memory reset/init, hashed-only storage, expiry, current/other device revocation, logout, temporary session invalidation and API/host/origin guards. UI logic checks cover Enter, Shift+Enter, composition/repeat, immediate clearing during a delayed request, newer draft preservation and failed-send recovery. Existing GPT, coding, web and updater regressions also run. These tests do not certify rendered browser/phone behavior or a real Windows restart; verify those locally after installation. v0.6.0 GPT operation was user-confirmed before this release.

Future work: desktop launcher/tray, smoother phone experience, voice and the abstract animated orb. See README-v0.6.md for GPT connection/capability details.
