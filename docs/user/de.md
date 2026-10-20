# DJConnect einrichten

**Your music. Your DJ.**

Dein persönlicher Musik-DJ in Home Assistant. Wünsche dir Musik, höre DJ-Beiträge und wähle die Stimmung deiner Session.

## Version auswählen

Diese Quelle beschreibt den Kandidaten **4.0.0-rc.1**, keine installierte Veröffentlichung.
Prüfe die Version in HACS. **3.3.1** verlangt eine Assist-Pipeline mit **STT und TTS**.
Der Kandidat benötigt einen verfügbaren Conversation-Agent; Sprache ist bei der
Einrichtung optional. Nur verfügbare Sprachwege werden angeboten.

## Voraussetzungen

- Home Assistant und HACS; Assist benötigt kein zusätzlich gekoppeltes Gerät.
- Spotify Direct: Premium, die **Client ID** deiner eigenen Spotify-Developer-App
  und eine externe **HTTPS**-URL von HA. Nabu Casa wird empfohlen, ist aber nicht Pflicht.
- Music Assistant: eingerichtete Installation und nutzbarer Player, ohne Spotify
  Client ID oder Spotify OAuth in DJConnect. **Later / manual** gibt es in beiden Versionen.
- Lokale Geräte im selben LAN koppeln; ESP32 benötigt 2,4-GHz-WLAN.

## Installieren und starten

1. Öffne den HACS-Link unten oder ergänze das Repository als **Integration** unter
   **Benutzerdefinierte Repositories**. Installiere DJConnect und starte HA neu.
2. Öffne **Einstellungen → Geräte & Dienste → Integration hinzufügen → DJConnect**.
3. Wähle Assist, lokales Gerät oder App. Bluetooth richtet optional nur das WLAN
   eines ESP32 ein; anschließend folgt die Kopplung.
4. Assist überspringt die Kopplung. Bei Bedarf koppeln: iPhone/Watch per QR, macOS mit angezeigter HA-URL und
   sechsstelliger Nummer, ESP32/Pi lokal. Abgelaufene Codes erneuern.
5. In 4.0 zuerst ein **Profile** auswählen oder erstellen. Wiederverwendung behält
   die Musikverbindung. Ein neues Profile wählt Spotify Direct, Music Assistant oder Later.
   In 3.3.1 wird zuerst das Backend ausgewählt und danach ein neues Profile angelegt.
6. Für Spotify eine App im Spotify Developer Dashboard erstellen. Die **genaue
   Redirect-URI aus dem Assistenten** dort eintragen, Client ID eingeben (kein Client Secret)
   und die Autorisierung abschließen. Nach Änderung der externen HA-URL die URI
   aktualisieren und erneut autorisieren. Music Assistant fragt nach seinem Player;
   Later verschiebt die Musikverbindung.
7. Im verbundenen Client eine DJ-Session starten oder **DJConnect DJ** in Assist
   auswählen. Eine verschobene Musikverbindung vor der Wiedergabe einrichten.

## Hilfe

Fehlt Assist, prüfe die Anforderungen deiner Version. Kehrt Spotify nicht zurück,
prüfe die genaue Redirect-URI. Bei Kopplungsfehlern LAN und Code prüfen. Bei einem
allgemeinen HA-Symbol erneut über HACS herunterladen, HA neu starten und Ansicht erneuern.

[HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration) · [Repository](https://github.com/pcvantol/djconnect) · [English / en](installation.md)
