# Verification Planning

The Verification Planning Engine expands abstract verification assets into
machine-readable execution plans. It does not execute scenarios, call adapters,
build artifacts, evaluate assertions or collect evidence.

Inputs:

- Scenario Catalog
- Verification Matrix
- Verification Data Framework
- Verification Modes
- Verification Policies
- Execution Environment capabilities
- Adapter and platform capability metadata

Output:

- execution plan
- execution graph
- execution batches
- resource plan
- environment plan
- coverage report
- runtime estimate
- expected evidence and reports

The canonical implementation lives in `tools/verification/planning`.
