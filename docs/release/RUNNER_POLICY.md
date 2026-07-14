# Platform Release Runner Policy

Status: `ARCHITECTURE_CORRECTED`

1. Platform source builds run only in GitHub Actions, never in Codex.
2. Qualified self-hosted runners are limited to Apple/macOS and Windows-native
   build jobs, protected to trusted internal events. A qualified macOS runner
   may additionally act as a deployment relay for a private local network only
   when a deployment target cannot be reached from GitHub-hosted infrastructure.
   A relay job performs no source build, artifact generation or publication.
3. HA, API, Website, ESP32 and Pi source builds use GitHub-hosted Linux.
4. Deployment targets never build source. Pi and ESP32 install qualified,
   published artifacts only.
5. Build evidence records source SHA, workflow identity, artifact hash and
   required Software Assurance and Trusted Delivery status.
6. Runner selection is a CI/artifact concern. Deployment uses only qualified
   published artifacts and target-scoped credentials; it never turns a Pi or
   ESP32 deployment target into a source-build runner. The local-network relay
   is a GitHub Actions execution path, not a deployment target or artifact
   producer.
