# Platform Release Operational Model

Status: `ARCHITECTURE_CORRECTED`

Codex orchestrates discovery, planning, version alignment, workflow dispatch,
evidence collection, Software Assurance, Trusted Delivery, qualification and
release decisions. GitHub Actions performs source builds; distribution
repositories publish qualified artifacts; deployment targets consume them.

```text
Codex control plane
  -> GitHub Actions source builds
  -> qualified artifacts and evidence
  -> distribution repositories / release channels
  -> optional deployment targets
  -> evidence-based closure
```

The internal gate is candidate SHA qualified, Verification evidence valid,
Software Assurance and Trusted Delivery `PASS`, coverage valid, version
alignment `PASS` and artifacts generated. Target availability is only required
when that release profile performs deployment.
