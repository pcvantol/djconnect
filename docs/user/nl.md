# DJConnect installeren

**Your music. Your DJ.**

Je persoonlijke muziek-DJ in Home Assistant. Vraag muziek aan, geniet van DJ-bijdragen en kies de mood van je sessie.

## Kies je versie

Deze bron beschrijft kandidaat **4.0.0-rc.1**, geen geïnstalleerde release.
Controleer de versie in HACS. In **3.3.1** is een Assist-pipeline met **STT én TTS**
verplicht. De kandidaat vraagt een beschikbare conversation-agent; spraak is
optioneel bij het instellen. Alleen beschikbare spraakroutes worden aangeboden.

## Nodig

- Home Assistant en HACS. Voor Assist is geen apart gekoppeld apparaat nodig.
- Spotify Direct: Premium, je eigen Spotify Developer-app **Client ID** en een
  externe **HTTPS**-URL van HA. Nabu Casa is aanbevolen, niet verplicht.
- Music Assistant: geconfigureerd en een bruikbare speler; geen Spotify Client ID
  of Spotify OAuth via DJConnect. **Later / handmatig** bestaat in beide versies.
- Koppel lokale apparaten op hetzelfde LAN; ESP32 gebruikt 2,4 GHz WiFi.

## Installeren en starten

1. Open de HACS-link hieronder, of voeg de repository als **Integration** toe bij
   **Aangepaste repositories**. Installeer DJConnect en herstart Home Assistant.
2. Open **Instellingen → Apparaten & diensten → Integratie toevoegen → DJConnect**.
3. Kies Assist, lokaal apparaat of app. Bluetooth kan optioneel alleen de WiFi
   van een ESP32 instellen; daarna volgt de koppeling.
4. Assist slaat koppelen over. Volg zo nodig de koppeling: iPhone/Watch via QR, macOS met de getoonde HA-URL
   en zescijferige code, ESP32/Pi lokaal. Gebruik een nieuwe code als de oude verloopt.
5. In 4.0 kies of maak je eerst een **Profile**. Hergebruik behoudt de bestaande
   muziekverbinding. Een nieuw Profile kiest Spotify Direct, Music Assistant of Later.
   In 3.3.1 kies je eerst de backend en vul je daarna een nieuw Profile in.
6. Voor Spotify maak je een app in Spotify Developer Dashboard. Kopieer de **exacte
   redirect-URI uit de wizard** naar die app, vul de Client ID in (geen Client Secret)
   en rond de autorisatie af. Werk de URI bij en autoriseer opnieuw als de externe
   HA-URL verandert. Music Assistant vraagt alleen om zijn speler; Later stelt muziek uit.
7. Start een DJ-sessie in de gekoppelde client, of selecteer **DJConnect DJ** in Assist.
   Stel een uitgestelde muziekverbinding eerst in voordat je afspeelt.

## Hulp

Assist ontbreekt? Controleer de voorwaarden voor jouw versie. Spotify keert niet
terug? Controleer de exacte redirect-URI. Koppeling mislukt? Controleer LAN en code.
Generiek HA-pictogram? Download opnieuw in HACS, herstart en ververs de frontend.

[HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration) · [Repository](https://github.com/pcvantol/djconnect) · [English / en](installation.md)
