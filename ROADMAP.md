# VEYRA direction and v1.0 criteria

VEYRA is a GPT-first Windows personal AI agent. Conversation is its interface: general file, PowerShell, browser and connected MCP tools should solve new tasks without a custom feature release for each request. Eligible ChatGPT plan sharing is preferred; Ollama is an optional local chat/fallback provider. Codex remains the coding specialist.

## Integrated v0.12 update

Implemented on `mega-update`: whole-PC automatic mode with explicit warning/confirmation, optional elevated worker after normal UAC setup, cron workflows, scoped SQLite memory, MCP, Playwright browser profiles, independent agents and recursive sub-agents, workspace previews, inbox/notifications, Stop All, shared limits, checkpoints, portable backups, unified desktop updates, local voice and an abstract listening/thinking/speaking orb. Implementation and verification are distinct; see [Development acceptance](docs/DEVELOPMENT.md) and [Testing](docs/TESTING.md).

Phone capability and a wake word are outside this update. Click the microphone to speak. An agent's workspace/context is separate, but a whole-PC agent is not an operating-system sandbox. Recursive work shares configurable depth, runtime, context, call and agent limits. The PC must be awake, signed in and running VEYRA for scheduled work; it cannot execute while Windows is shut down or asleep.

## v1.0 readiness

Keep 0.x versions until the complete daily-use experience is dependable:

1. Fresh installation and upgrades preserve conversations, names, pairing, provider credentials, projects and model caches.
2. Chat, Auto routing, PC actions and Codex work together with the user's real provider account, including errors and reconnects.
3. Whole-PC permissions, reviewed/automatic actions, revocation, cancellation and administrator enrollment behave clearly on an ordinary Windows PC.
4. Scheduled and recursive work survives interruption with honest partial results and no silent mutation replay. Representative installation tasks include dependency installation and independently verified execution.
5. Physical microphone/speaker selection, voice latency, interruption and the conversation/orb UI are comfortable in daily use.
6. The installer and one-touch updater work through a real installed-version upgrade, with rollback/recovery and clear error messages.
7. Accessibility, packaging notices, dependency maintenance and a representative acceptance suite are ready for public distribution.

Review observed daily-use issues and agree the remaining scope before calling the product 1.0. A green CI run and a larger feature list alone do not establish that milestone.

## Later work and discussed ideas

Additional providers (DeepSeek, Grok and Claude), supported native visual desktop interaction, broader MCP authentication, performance improvements and stronger workflow editing are future candidates. Their authentication, cost and capabilities must be verified before claiming support. Private phone access can be revisited separately; it is not a prerequisite for this Windows-focused mega-update.

The public app is VEYRA, “Your AI. Your computer. Your rules.” Each user names their assistant independently; Nova is the example. Preserve legacy internal identities where they protect installed data. For each release, replace README's current feature list and append history to the single CHANGELOG; do not add per-version README/changelog files.
