# Spotify Direct setup

These requirements apply to both integration3.3.1 and candidate4.0.0-rc.1 when
**Spotify Direct** is chosen. Music Assistant and Later/manual do not require
DJConnect Spotify authorization. Reusing an already connected Profile does not
require new credentials merely because another client is paired.

1. Use Spotify Premium and create your own app in the
   [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Start the DJConnect wizard and choose Spotify Direct where your version asks
   for the backend. Supply an external **HTTPS** HA URL; Nabu Casa is recommended
   but not mandatory. This requirement is for Spotify authorization, not all pairing.
3. Copy the **exact redirect URI shown by the current wizard** into the Spotify
   app's redirect list. Do not invent a callback URL from an example or setup code.
4. Enter the app's **Client ID**. DJConnect does not ask for a Client Secret.
5. Complete Spotify authorization when HA opens it, then return to the wizard.
6. Choose an available playback target before requesting music. If the external
   HA URL changes, update Spotify's redirect registration and reauthorize using
   DJConnect integration options or the offered HA repair.

[Installation](installation.md) · [Stable guide](stable-3.3.1.md) · [Help](troubleshooting.md).
