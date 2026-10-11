# Maintained dependencies

Generated from djconnect-platform-v1.json, maintenance DJC-DJ-PRESENCE-ROADMAP-DESIGN-V1-20261011.

The original3October snapshot/audit/source pins and projections are immutable history in [history/20261003](history/20261003/README.md). Only this bounded delta is current here; inherited premerge statuses are not current blockers. Only the selected existing Core writer is admitted by implementation receipt; no automatic dispatch, second writer or native/installed/hardware acceptance.

| Producer → consumer | Kind / phase / gate | Hard | AND/OR | Required subset | Evidence |
|---|---|---|---|---|---|
| `SLICE::CORE::DJ-PRESENCE-CONTRACT` → `SLICE::CORE::DJ-PRESENCE-POLICY` | implementation_contract / implementation / start | True | AND | Exact policy table/default/ownercontract | Pinned contract and producer fixtures |
| `SLICE::CORE::DJ-PRESENCE-CONTRACT` → `SLICE::APPLE::DJ-PRESENCE-CONTROL` | implementation_contract / implementation / start | True | AND | Contract-dependent native integration; independent UX preparation may proceed | Early pinned candidate/fixtures suffice, not all Finalization documents |
| `SLICE::CORE::DJ-PRESENCE-POLICY` → `QUAL::VIBECAST::DJ-PRESENCE-COMPAT` | integration_acceptance / integration_acceptance / completion | True | AND | Actual varied authorized Broadcast traces | Exact producer local/static browser receipts; CAF/native/hardware separated |
| `SLICE::CORE::DJ-PRESENCE-POLICY` → `QUAL::PRODUCT::DJ-PRESENCE-V1` | integration_acceptance / integration_acceptance / completion | True | AND | Policy AND native control AND both renderer consumers | Exact candidate/contract/consumer receipts, acceptance A-E |
| `SLICE::APPLE::DJ-PRESENCE-CONTROL` → `QUAL::PRODUCT::DJ-PRESENCE-V1` | integration_acceptance / integration_acceptance / completion | True | AND | Policy AND native control AND both renderer consumers | Exact candidate/contract/consumer receipts, acceptance A-E |
| `QUAL::VIBECAST::DJ-PRESENCE-COMPAT` → `QUAL::PRODUCT::DJ-PRESENCE-V1` | integration_acceptance / integration_acceptance / completion | True | AND | Policy AND native control AND both renderer consumers | Exact candidate/contract/consumer receipts, acceptance A-E |
| `QUAL::PRODUCT::DJ-PRESENCE-V1` → `PROJ::INTELLIGENCE::DJ-PRESENCE` | integration_acceptance / integration_acceptance / completion | True | AND | Joint product completion, not slider-only completion | Core + Apple owning receipts; no extra writerlane |
| `SLICE::CORE::ACTIVE-SESSION-MOOD` → `PROJ::INTELLIGENCE::DJ-PRESENCE` | strategy_order / selection / start | False | AND | Mood completion orders selection, never determines presence frequency | Source1146/Finalization1147; resource/writerslot admission remains outside functional DAG |
| `SLICE::CORE::ACTIVE-SESSION-MOOD` → `SLICE::CORE::DJ-PRESENCE-CONTRACT` | implementation_contract / implementation / start | True | AND | Only ordinary pairing, server-owner, active Session, final authority and CAS/readback subset | Qualified ACTIVE_SESSION_MOOD_V1.md, no Mood endpoint extension |
| `PROJ::INTELLIGENCE::DJ-PRESENCE` → `PROJ::ROADMAP::NARRATIVE-LYRICS` | strategy_order / selection / start | False | AND | Later richer presenter maturity reuses v1; broader Deferred family remains Deferred | No retrospective v1 completion gate or new semantic relationship dispatch |
