# TREN v0.6.0 — GPT conversation layer

Update using Settings → Updates → Check → Download → Install & restart. Then pair again (persistent device sessions are still planned).

## Connect once

On your Windows PC, open Settings → ChatGPT conversation → Connect ChatGPT. Finish the official browser sign-in and grant TREN plan-sharing permission. The consent screen controls eligible plan usage and app limits. Successful consent makes ChatGPT the preferred conversation provider. No API key, separate API billing, Codex token reuse or private ChatGPT endpoints are configured.

Use Refresh available models to see the account's visible model catalog. The default follows server order; choose a returned model explicitly if desired. Models are discovered with the same OAuth credential used for inference. Plan eligibility and availability are account-dependent; a permission or usage-limit failure is shown clearly.

Ollama remains selectable for local chat. Optional fallback is off initially: turn it on and save preferences if you want ChatGPT failures to use Ollama. Fallback replies are labelled. Codex continues to handle coding/review with its separate existing login. Scheduled routines currently remain on Ollama.

## Continuity and capabilities

TREN sends recent chat (up to 16 messages, bounded context) and up to 30 saved notes to the selected model. Notes, reminders and chat stay in TREN's SQLite database. ChatGPT account memory and this project's development conversation do not automatically transfer. Explicit /remember and /remind still work without a model request.

ChatGPT supplies conversational text. TREN uses existing read-only web search/page tools for explicit search requests, current/latest/today requests and supplied HTTP(S) URLs, then sends bounded evidence for the response. This is a simple grounding pass: one search and one page or one supplied URL, not a model-directed web research loop. Results/failures appear in Activity. Other live lookups can use Web search or Ollama. Web access off disables these lookups; choose Ollama too for offline conversation. This release does not add desktop control, voice, email, purchases, code execution through GPT chat or an animated avatar.

Replies are saved only after a complete response. Late plan-limit errors or interrupted streams never save partial text as success. ChatGPT-labelled replies, Ollama fallback replies and local command results retain their provider labels across restart. Older chat rows are migrated as Ollama.

## Credentials and requirements

Python 3.11+; Windows; Node.js already installed for Codex (Node 22+ recommended). The Python standard library implements the documented public OAuth/Responses protocol. Node's built-in crypto verifies RS256 ID token signatures against issuer JWKS; no SDK package downloads are needed.

Tokens are encrypted with Windows DPAPI for the current Windows user and written atomically to data/chatgpt/connection.dpapi. They are never returned in browser state, URLs, command arguments or error text. Sign-in opens on the TREN PC with a short-lived loopback listener, state/nonce/PKCE checks and registered client validation. Client registration and an opaque host ID persist across attempts. Rotating refresh tokens are checkpointed before identity-key checks, so a key-service outage can recover on a later request. Disconnect removes local credentials and attempts remote revocation; if remote revocation fails, a notice asks you to disconnect TREN in ChatGPT Settings. Copying the credential file to a different Windows account will not decrypt it. This first integration retains one original ChatGPT account; multiple profiles/account switching are not implemented.

The app updater uses only previously allowed filenames. v0.5.1 can install this release without changing the updater allowlist. Current data, Codex auth and model installations remain intact. Finish/cancel ChatGPT sign-in before installing an update.

## Verification status

Automated tests cover simulated browser callback/PKCE, granted scopes, identity claims, real RSA signature/tampering, rotating-token outage/restart recovery, catalog filtering, streamed terminal errors, origin/redirect rejection, protected-store error preservation, paired API routes, memory/history/provider persistence and opt-in fallback. The production Windows DPAPI path, real account consent/plan eligibility and a live GPT reply still require verification on Windows after installation. The UI has logic/HTML checks; rendered browser/phone QA is not certified here.

Official protocol references:
- https://developers.openai.com/siwc/token-sharing-open-source/sign-in
- https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference

No official SDK code or bundled third-party packages are distributed in this release.
