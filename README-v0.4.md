# TREN v0.4 — conversation first

Stop TREN. Extract update into a new folder, run upgrade.bat, enter your existing installation folder. Run start.bat from that existing folder and refresh browser (Ctrl+F5). No dependencies/model installs. Code backup and database snapshot are private; current data, projects, pairing and hosts remain untouched.

Conversation is the main interface. Auto recognizes common coding phrases and /code. Build forces Codex edits; Review forces read-only Codex; Chat forces Ollama. Follow-up requests should use Build/Review or Continue this project. Coding requests open a permission dialog; Start task authorizes the displayed project/mode. Advanced request/expected-file/timeout fields remain editable. Named file paths from requests are suggestions; review them if a request mentions input files. Last project is remembered per browser.

Progress, Cancel, results and expandable file text appear beside chat. Enter sends, Shift+Enter adds a newline. Existing web, notes, routines, activity and coding controls remain under Tools. Settings preserves connections/data/phone controls. General chat/research remains Ollama; coding uses existing Plus-authenticated Codex. No paid API fallback.

Gaming holds queued work; active jobs continue. Cancel leaves written files. Clear chat only deletes Ollama messages; coding history remains. No voice/PWA, complete diffs, arbitrary external project directories or autonomous natural-language scheduling added.

Rollback: stop TREN and use the command printed by upgrade.bat. From extracted update folder run py -3 upgrade.py --rollback "C:\path\Tren-Local\backups\pre-v0.4-TIMESTAMP". Previous code/docs return, current data remains. See LOCAL-VERIFICATION.md and TEST-RESULTS-v0.4.md.
