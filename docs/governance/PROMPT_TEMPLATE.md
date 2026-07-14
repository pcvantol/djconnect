# Canonical Engineering Prompt Template

Use exactly one complete copy-pasteable prompt in one code block for each
engineering increment. Populate every applicable field from current repository
evidence; do not infer scope from historical chat.

```text
Prompt ID:
Title:
Generation and engineering program:

Initialization (mandatory, before planning):
- Repository Synchronization: `git switch main`, then `git pull --ff-only`; stop on failure.
- Current Main Verification: branch, HEAD, upstream, fast-forward status, working tree and repository cleanliness; stop on failure.
- Canonical Repository Read: follow `BOOTSTRAP.md` through active roadmap/backlog and `PROMPT_INDEX.md`.
- Implementation Reality Check: inspect existing functionality, validation, qualification and documentation; do not reimplement an existing outcome.
- Engineering Planning: determine the current increment, program, repository truth, backlog, deferred work and recommended next prompt from current main.

Objective:
Repository truth verified:
Current roadmap and backlog evidence:

In scope:
Out of scope:
Architecture and ownership constraints:

Acceptance evidence:
Required documentation updates:
Deferred-work handling:

Initialization checks:
- do not assume predecessor, current increment or repository status from chat
- preceding PR merged and remote branch removed
- prior Prompt History archived
- synchronized current main and status records verified
- repository clean

Finalization:
- validate and retain evidence
- update ENGINEERING_STATUS, REPOSITORY_STATUS, MANAGEMENT_SUMMARY and PROMPT_INDEX
- create one immutable Prompt History record
- create exactly one reviewable pull request
- stop at the freeze point
```
