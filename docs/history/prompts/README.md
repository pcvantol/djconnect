# Prompt History

This directory contains one immutable record for every completed engineering
prompt. It supports traceability, architecture rationale, audit and historical
context. It is never the authority for current implementation state; current
`main` and the status/roadmap records are authoritative.

Do not edit an archived record. Corrections are recorded by a later prompt.

Each record must include:

- Prompt ID and title
- Generation and engineering program
- Branch, commit and pull request
- Decision and execution date
- Validation
- Created and updated timestamps
- Known limitations
- Deferred work
- Recommended next prompt

Use one Markdown file per prompt, named with its execution date and stable
prompt identifier.
