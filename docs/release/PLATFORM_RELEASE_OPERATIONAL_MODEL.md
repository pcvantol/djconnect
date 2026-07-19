# Platform Release Operational Model

Status: `ARCHITECTURE_CORRECTED`

Codex orchestrates discovery, planning, version alignment, workflow dispatch,
evidence collection, Software Assurance, Trusted Delivery, qualification and
release decisions. GitHub Actions is the exclusive execution engine: it
performs source builds and owns tagging, releases, artifact publication,
deployment and supported rollback. Distribution repositories publish qualified
artifacts; deployment targets consume them. The Runtime has no direct mutation
path.

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

## Operational burn-in procedure

Operational burn-in is the bounded observation phase that follows successful
Internal Release deployment and post-deployment smoke. It establishes whether
the already-qualified, immutable release behaves stably across its declared
operational targets before the release can be considered for Release
Certification. It is an evidence-collection activity, not a release,
deployment, workflow, manifest or runtime change.

The procedure is reusable for every Platform Release. A burn-in record is
always bound to one immutable release manifest, its exact artifact identities
and its declared target scope. A candidate, artifact binding, target scope or
runtime correction that changes during the window invalidates the affected
burn-in record; the affected scope must enter a new window after its normal
deployment and smoke evidence is complete.

### Objective, scope and duration

The objective is to collect sufficient operational evidence that the declared
Internal Release remains available, compatible and free from release-blocking
runtime incidents for a continuous observation window.

The scope is only the targets, artifacts and release capabilities already
declared in the immutable manifest. It does not expand verification scenarios,
re-run qualification, infer new deployment requirements or impose new
automation. Existing target telemetry, deployment records, post-deployment
smoke evidence, incident records and release evidence are used where they
exist.

Before burn-in starts, its evidence plan declares a continuous duration. The
standard Internal Release duration is seven consecutive calendar days; a
longer duration may be declared for a release when its scope or known
operational risk requires it. The declared duration, start time and end time
are immutable evidence fields for that burn-in attempt.

For Platform Release 3.3, the monitored target set is the qualified Internal
Release scope: API Workers, Website Pages, Raspberry Pi, ESP32, Apple macOS,
Apple iPhone with paired Apple Watch validation, iPad, Windows ARM64 and Home
Assistant Pi 5. The 3.3 burn-in starts only after the applicable target
deployment and post-deployment smoke evidence is recorded for the exact bound
artifacts.

### Entry criteria and operational checklist

Burn-in may start only when all of the following are true:

- the release manifest, artifact identities and target scope are immutable and
  traceable;
- every in-scope target has successful deployment evidence and separate
  post-deployment smoke evidence for those identities;
- the release qualification inputs remain valid and contain no unwaived
  release-blocking finding;
- the observation duration, target owners, evidence locations and escalation
  contacts are recorded; and
- no active release-blocking incident affects an in-scope target.

During the window, the operator records observations using existing sources
without introducing a new automation path:

- confirm that each target remains reachable or otherwise available through
  its existing operational signal;
- record startup, restart, crash-loop or sustained-error observations where
  those signals already exist;
- retain the bounded compatibility signals already used by target smoke, such
  as version read-back, authenticated handshake and required route health;
- record target-specific functional degradation or user-impacting incidents
  reported through normal operations; and
- record the observation time, target, source, result and incident reference
  for each material observation.

Burn-in does not require raw logs, credentials, prompts, user data or new
continuous monitoring. Evidence remains redacted and referenced from its
authoritative producer.

### Evidence, failures and escalation

The burn-in evidence bundle must contain the immutable manifest identity,
artifact identities, target list, declared window, entry-criteria result,
target observation ledger, incident/exception register, references to the
existing deployment and smoke evidence, and an explicit end-of-window result.
Each item identifies its source, timestamp and redaction posture. Missing
evidence is not treated as a successful observation.

The following are burn-in failures:

- a release-blocking availability, compatibility, integrity or runtime
  incident on an in-scope target;
- a regression that invalidates required target smoke or prior qualification
  evidence;
- a change to the bound candidate, artifact, scope or required target during
  the window; or
- incomplete, untraceable or unredacted required evidence at window close.

On failure, stop the affected burn-in window, preserve the evidence and record
the incident against the exact target and artifact identity. Escalate first to
the owning target or repository maintainer and the Platform Release operator.
Use the existing release recovery and incident process for any required
remediation; do not alter the manifest, deployment workflow or runtime as part
of burn-in. A corrective candidate follows its normal qualification,
deployment and smoke path before a new affected-scope burn-in window begins.

### Completion and Release Certification relationship

Burn-in completes successfully only when the full declared window has elapsed,
all in-scope targets have the required observations, no unresolved
release-blocking incident remains, and the evidence bundle is complete,
traceable and redacted. The completion record is `BURN_IN_COMPLETE`; any other
result remains incomplete or failed and cannot be interpreted as a pass.

Successful burn-in is an input to, not a substitute for, Release
Certification. It permits the exact evidence bundle to be submitted to the
separate certification decision defined by Prompt 5. It neither certifies the
release nor authorizes publication, deployment, rollback or a change to the
release scope.

## Native runner alignment

Apple and Windows native source-build paths are qualified as of 2026-07-13.
Apple run `29246454969` built and uploaded an unsigned macOS artifact on
`djconnect-apple-macos`; Windows run `29246684022` built and uploaded an
unsigned Windows artifact on `djconnect-windows11-parallels`. The corresponding
runner evidence is recorded in `RUNNER_QUALIFICATION_REPORT.md`.

```text
NATIVE_RUNNER_ALIGNMENT_COMPLETE
PLATFORM_RELEASE_3_3_INTERNAL_READY
```
