# TREN release process

Canonical public repository: alecjhalpin/TREN. The release workflow publishes new stable versions from main after build/test validation. Current version is in version.json. Change it to a newer three-part version for a release; an already-published version is skipped and its assets remain unchanged.

The published asset is TREN-vX.Y.Z.zip with an internal checksum manifest. GitHub adds an asset SHA-256 digest, which the in-app downloader verifies. GitHub-generated source archives cannot be installed as updates. No GitHub token is stored by TREN; Actions uses the repository token with contents:write.

The updater accepts public stable releases, newer versions, bounded ZIPs and allowlisted paths. It preserves current data/configuration and backs up code before restart. Read README-v0.5.md for rollback and limits. Hashes detect corruption under the selected trusted source; no independent publisher signature is implemented.
