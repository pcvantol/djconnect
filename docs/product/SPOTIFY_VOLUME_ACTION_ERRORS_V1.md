# Spotify output volume errors v1

Core owns the normal command transport and actual Spotify capability projection.
Apple renders an action-local localized error and retains independent playback,
Session, DJ text and voice status. This repair adds no owning writer or new route.

## Projection and failure contract

Preserve the provider device supports_volume boolean exactly in both available
outputs and current playback. Missing/non-boolean means null/unknown, never
support inferred from is_restricted, name or type. is_restricted remains its own
independent provider field. Current provider status remains authoritative; do not
persist a synthetic global outage or permanent volume capability from a failed
command. A fresh status/output read can replace the earlier observation.

For set_volume and volume_delta, a Spotify403 response containing the specific
Cannot control device volume reason becomes the existing capability exception.
A different403, authentication error, timeout or503 is not evidence of an
unsupported device. No extra provider request or automatic retry is introduced.
Existing normal Spotify401 refresh policy remains unchanged.

Both ordinary paired command paths return an action-local failure (HTTP200):
- Proven capability refusal: success:false, error:unsupported_backend_capability,
  capability:supports_volume, backend:spotify_direct, backend_available:true.
- Other volume failure: success:false, error:volume_command_failed. Omit
  backend_available: the failed action establishes no independent global health.
Both include command (set_volume or volume_delta), error_scope:command and
retry_automatically:false. message is the stable error code, not provider prose;
clients own its five-language rendering. No text/dj_text/audio/playback fallback
or stale cached track is added. This does not change other commands' error policy.

Do not write runtime last_error/last_dj_text, backend availability, voice/Session
state or provider capability cache when translating either command failure.
The delta path's ordinary preceding status observation remains a real read;
its read failure must also stay within the failed volume operation. Invalid
numeric input remains the established invalid-command contract, not capability.
A returned success:false must never be wrapped in a successful delta response.

## Evidence boundary

Fast offline regressions cover the actual Spotify response seam, both command
paths, explicit true/false/unknown output metadata, rejected/failed operations,
returned failure results, unchanged runtime state and unrelated status errors.
All provider replies and credentials in those probes are synthetic. They prove
source behavior, not real iPhone volume support or native/audio acceptance.

References: Spotify's current playback device schema and volume endpoint:
https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback
https://developer.spotify.com/documentation/web-api/reference/set-volume-for-users-playback
