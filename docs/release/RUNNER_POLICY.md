# Platform Release Runner Policy

Status: `ARCHITECTURE_CORRECTED`

1. Platform source builds run only in GitHub Actions, never in Codex.
2. Qualified self-hosted runners are limited to Apple/macOS and Windows-native
   build jobs, protected to trusted internal events.
3. HA, API, Website, ESP32 and Pi source builds use GitHub-hosted Linux.
4. Deployment targets never build source. Pi and ESP32 install qualified,
   published artifacts only.
5. Build evidence records source SHA, workflow identity, artifact hash and
   required Software Assurance and Trusted Delivery status.
