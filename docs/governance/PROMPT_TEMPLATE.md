# Canonical Engineering Prompt Template

Use exactly one complete copy-pasteable prompt in one code block for each
engineering increment. Populate every applicable field from current repository
evidence; do not infer scope from historical chat.

```text
Prompt ID:
Title:
Generation and engineering program:

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
- preceding PR merged and remote branch removed
- prior Prompt History archived
- current main and status records verified
- repository clean

Finalization:
- validate and retain evidence
- update ENGINEERING_STATUS, REPOSITORY_STATUS, MANAGEMENT_SUMMARY and PROMPT_INDEX
- create one immutable Prompt History record
- create exactly one reviewable pull request
- stop at the freeze point
```
