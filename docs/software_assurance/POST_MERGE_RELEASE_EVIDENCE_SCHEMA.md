# Post-Merge Release Evidence Schema

Schema version `1` evidence has kind `post_merge_release_evidence` and requires
`repository`, `main_sha`, `main_parents`, `originating_pr`,
`source_qualified_pr_sha`, `pre_merge`, `post_merge`, `provenance_result`,
`decision`, `timestamp` and `evidence_digest`.

`main_sha` is the release identity. `source_qualified_pr_sha` must identify the
final PR head and must not be substituted for `main_sha`. `decision` is exactly
`POST_MERGE_RELEASE_EVIDENCE_QUALIFIED` or
`POST_MERGE_RELEASE_EVIDENCE_NOT_QUALIFIED`.
