# Parallel offline CI

Core's Validate and TDE observe workflows run the complete offline unittest
discovery in four processes for normal tests and coverage. Lint, security,
verification-framework and governance jobs already run independently. The
reusable integration workflow keeps its serial default for other repositories;
Core explicitly opts into the runner and its evidence upload.

`tools/run_parallel_unittest.py --jobs 4 --report-dir <fresh-external-directory>`
discovers the same suite in the coordinator and every worker. It assigns whole
modules to bounded workers, retaining discovery order and class/module fixture
semantics. Workers get separate TMPDIR/TEMP/TMP directories and logs. No tests
are filtered out, no failure triggers a serial fallback or automatic retry, and
no timeout, assertion or expected skip is relaxed. Reports reconcile every test
ID exactly once, including ordinary class/module fixture skips; missing worker
reports, process crashes, import errors and differing discovery fail closed.
Custom TestSuite subclasses require explicit runner support rather than silent
flattening. These are offline tests only: paid model tests, HA installations,
provider operations and device effects must not be added to this parallel pool.

`--coverage` gives each worker its own coverage database. Exact dataset inventory,
readability, nonempty measured lines and compatible branch modes are checked
before combining. Original databases and XML remain inside the exclusive report
directory, so simultaneous local runs do not share output files. CI copies only
the successful XML to the existing consumer path. Coverage XML and the
exact main-SHA marker keep their existing artifact names and release binding;
worker plans, JSON results and logs are separate evidence artifacts. Success is
recorded only after coverage generation succeeds. A fresh exclusive report
directory prevents stale results from being reused.

Local runs should place report directories under the configured Shared Data
temporary root. CI uses its own runner temporary directory. Shared external
fixtures must provide their own isolation; process isolation does not authorize
concurrent effects against one real service. Protected Source, separate Final,
qualification, artifact publication and deployment keep their required order.
Dependency graphs must retain those gates; independent jobs may overlap.

Runner regressions exercise actual overlapping processes, independent temp
directories, shared class fixtures within a module, all outcome types, worker
crashes, import failure, ordinary fixture skips, stale evidence rejection and
coverage of test-body-only lines from both workers. Missing, corrupt and
incompatible datasets are explicitly rejected. The content-deletion transition
fixture uses its own runtime module and installs its intended source moment,
so it does not depend on earlier suites' module teardown/reload order. The GitHub
firmware fixture installs/restores its required actual constants instead of
borrowing another suite's minimal stub. CoverageData is bound before discovery
can expose the internal verification module named coverage on the import path.
