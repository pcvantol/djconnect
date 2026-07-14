# Repository Hygiene

**Status:** Canonical operational policy

Before an engineering prompt begins, verify that the preceding branch is
merged, its remote branch is removed, its Prompt History is archived and the
working tree is clean. Delete the preceding local engineering branch only after
all four checks succeed.

Cleanup fails closed: if merge, remote deletion, archival or cleanliness cannot
be verified, do not delete branches and do not start the next increment.

The current increment must also finish clean after its scoped changes are
committed. This policy concerns engineering branches; it does not replace the
Verification Platform's runtime hygiene gates.
