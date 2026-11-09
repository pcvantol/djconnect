# Core 4.0.0 external TestFlight qualification

On 9 November 2026 the owner explicitly deferred the open Ask DJ
real-quality qualifications so external TestFlight could proceed. The
deferred work consists of the 68 open EN/NL or cross-language findings in
the exact [Ask DJ release report][golden] for Core
`67d3c98543ce4d2d2330e40bd0ea4565286e4a7c`. The 50 deterministic owner
suites, 112 single-turn cases and 560 proactive cases passed for that
candidate. The 60 Help cases are included in the single-turn count.

The findings keep their open status in the Ask DJ qualification inventory.
The real-model qualification remains outstanding. Resolve the findings
and complete the full EN/NL qualification before the regular Home Assistant
release. The standard artifact and HACS gates continue to apply there.

The beta exception covers one exact Core candidate for an external
TestFlight test environment. The dedicated manual workflow verifies the
successful [Core main CI run][ci] and the hash of the original report before
it packages the candidate. It emits a separate Actions artifact and records
the deferral in its receipt. A different candidate requires a new decision
and matching evidence. Deployment and installed smoke require their own
target binding. Apple signing, external TestFlight distribution, native
acceptance and audible acceptance require their own evidence.

## Deferred work on Dutch composer contributions

[Core PR #1539][credit-pr] was closed without merging on 9 November 2026.
The candidate is preserved at
`5637c7e1ab7f6ac8cd5384478af61d8bae8de822` on
`codex/askdj-credit-telling-nl`. The factual and Dutch-language reviews
passed on the last candidate. Style review withheld publication, so
editorial acceptance remains open.

Resume from the preserved branch. Obtain live editorial acceptance for
both the selected Dutch contribution and its follow-up on the exact
candidate before reopening the change for merge or marking it qualified.

[credit-pr]: https://github.com/pcvantol/djconnect/pull/1539
[golden]: https://github.com/pcvantol/djconnect/actions/runs/42693949233/artifacts/13709630115
[ci]: https://github.com/pcvantol/djconnect/actions/runs/42692912767
