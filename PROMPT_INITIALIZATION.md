# Prompt Initialization

**Status:** Canonical operational contract

Every engineering prompt must begin with this sequence, in order:

```text
Repository Synchronization
  -> Current Main Verification
  -> Canonical Repository Read
  -> Implementation Reality Check
  -> Engineering Planning
```

## Repository Synchronization

Run `git switch main` and then `git pull --ff-only`. If either fails, stop.

## Current Main Verification

Verify the checked-out branch, current `HEAD`, tracking branch, fast-forward
status, working-tree cleanliness and repository cleanliness. If any check
fails, stop.

## Canonical Repository Read

Follow `BOOTSTRAP.md` exactly. Read current status, roadmap and backlog before
consulting history. Prompt History is optional context only; conversation
history is never current-state authority.

## Implementation Reality Check

After synchronization, inspect the requested functionality, its validation,
qualification, documentation and implementation. Do not reimplement an
existing outcome; close only remaining evidence-backed gaps.

## Engineering Planning

Use synchronized current main to determine the current engineering increment,
program, repository truth, backlog, deferred work and recommended next prompt.
No prompt may assume those facts from its text, conversation context or
historical planning.
