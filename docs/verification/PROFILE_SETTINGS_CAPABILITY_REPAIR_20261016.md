# Shared settings capability advertisement repair

Post-merge installation preparation for source #1193 / Finalization #1194
found the generic HTTP/WebSocket `contract_versions.profile_session_settings`
still advertised 2 although the delivered owner route accepts contract3.
A consumer selecting the advertised version would receive an upgrade error.
The pending, not-yet-loaded HA-dev source was restored to its previous verified
installation; HA-prod was not changed. Neither environment was restarted.

The repair derives this one advertisement from the existing typed
`SETTINGS_VERSION` constant and refreshes the public capability fixture.
A regression validates a request using the advertised version through the actual
owner-route request validator. This does not introduce another settings contract,
migration, provider, consumer change or product slice. Speech's envelope remains
version1: its existing `prepare_contracts` separately advertises prepare1/2/3.

The settings, authorization, storage and publication implementations remain those
already qualified in #1193. Installed/native/audible acceptance is separate;
installation resumes only after exact protected merge/artifact qualification.
Golden Scenario behavior is unchanged: this corrects capability discovery for
an existing owner route without altering music, Session or Moment generation.
