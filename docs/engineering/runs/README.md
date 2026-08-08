# Engineering Run Handoffs

This directory is the durable, sanitized repository handoff for successfully
finalized Engineering Platform transactions. `latest.md` and `index.json` are
the deterministic discovery entry points. Local operational reports remain
under `.engineering/` and are never copied here.

The Finalization PR generates and commits these records before it is merged.
The Execution Host never writes tracked handoff files after repository cleanup;
that preserves the `WORKSPACE_READY` guarantee on the synchronized `main`
checkout.
