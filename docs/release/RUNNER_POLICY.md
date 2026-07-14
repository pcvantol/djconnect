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
7. The macOS runner has exactly three independent capabilities: Apple Native Build Runner,
   Private Network Deployment Relay and Apple Secure Distribution Relay. They
   have distinct jobs, permissions, secrets, workspaces, target allowlists and
   evidence records. Apple Native Build is CI / Qualification or Artifact Build;
   the two relay capabilities are Deployment-only. A relay may consume only an
   approved manifest-bound qualified artifact, perform one allowlisted target
   mutation and record redacted evidence; it is not a general-purpose
   private-network automation runner.
8. Apple Secure Distribution Relay signing uses only the runner-local signing
   environment. Apple certificates, private keys and provisioning profiles are
   never GitHub secrets, workflow artifacts or deployment evidence. The relay
   never compiles source or generates unsigned Apple artifacts.
9. Apple Native Build has no private-network deployment credentials. Private-
   Network Deployment Relay has no Apple signing credentials. Apple Secure
   Distribution Relay has no Pi SSH, Home Assistant or ESP32 deployment
   credentials.
10. The qualified macOS relay may run bounded post-deployment smoke checks only
    in a separate deployment-evidence job and only against manifest-allowlisted
    private targets/routes. Smoke is read-only, cannot scan the network or
    mutate a target, and is not a Verification Platform job. Its credentials,
    workspace and evidence remain target-scoped and isolated from Apple build
    and Apple secure-distribution jobs.
