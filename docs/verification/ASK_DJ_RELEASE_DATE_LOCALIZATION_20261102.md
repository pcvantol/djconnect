# Ask DJ localized edition dates — 2 November 2026

The reported Dutch reply interpolated the validated ISO source value directly:
`De albumuitgave met Promise vermeldt 2024-12-20 als releasedatum.`
The same local observation route now formats only its displayed date slot using
the effective app/request language, giving `20-12-2024` in Dutch.

Canonical families use nl DD-MM-YYYY, en MM/DD/YYYY, de DD.MM.YYYY and
fr/es DD/MM/YYYY. Month-only dates use the same separator and retain only month
and year; year-only values remain unchanged. Regional request tags continue to
normalize to the existing five language families. The host locale is not used.

The structured `release_observation.release_date` remains original ISO and
`precision` stays unchanged. Date validation, current/selected item identity,
source, original expiry, session and track-change guards are untouched. Work
titles containing date-like text stay literal. No new lookup, model, playback
operation, history rewrite, device effect or language qualification is added.

The new application-route test reproduces the screenshot with Promise and
2024-12-20 across five app-language tags, all three precisions, and a work title
containing the literal ISO date. Before the product fix it produced 12 failures
and five passing year-only subtests; the original failing log is retained.
After the bounded formatting fix, seven release-route tests plus40 subtests
PASS, including existing current/selected metadata and expiry/race cases.
Broader dialogue and playback observation regressions: **222 PASS,165 subtests**
(9.66s). Ruff and diff checks pass. These are cost-free local fixture tests;
no paid model, real provider or installed/native test was run.

Baseline protected Core is `6a1403a9b41a98d82473aefdde344508d56602b0`.
Only the observation presentation product file changes; all other301 product
files, manifests, normative release contracts and release inputs stay equal.
Fresh native host verification before implementation: exit0/MATCH/onboarding4.5.6.
Independent source/exact review, normal protected delivery and a separate Final
remain required. Installation and actual app acceptance must be recorded
separately; this source note does not claim the phone already shows the fix.

## Fresh current-source HA proofs

Independent review caught a mandatory current-product pin failure in the old
recording-production HA fixture; it was not relabelled or waived. All24 existing
isolated HA groups were actually rerun on these302 product hashes in six unique
network-none containers. Source bytes matched before/inside/after; all groups
passed and each own container was verified absent. External provider/model and
native boundaries remain explicitly synthetic or NOT_RUN.

The22 current proof aliases are reconstructed from those new original RAW,
admission and result receipts. All22 prior fixture bytes and old originals are
retained privately, and earlier historical fixtures keep their own scope.
The full four-worker offline suite with coverage follows this genuine refresh;
its plan, worker logs, reconciliation and summary are retained as freeze evidence.

The first full run exposed one derived recent-list example still containing the
previous run's timestamp. Its prior bytes and failed full report are retained.
Only that example was copied from the **same new original** receipt's extension;
product, harness and RAW bytes were unchanged, so no HA run was repeated.
The corrected four-worker full run passes: **4,412 discovered/run/accounted,
seven existing skips, zero failures/errors**, 52.875s, with reconciled coverage.
