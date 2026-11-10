# DJConnect installeren

**Your music. Your DJ.**

Je persoonlijke muziek-DJ in Home Assistant. Vraag muziek aan, geniet van DJ-bijdragen en kies de mood van je sessie.

## Voor je begint

DJConnect **4.0.0** vereist Home Assistant **2026.11.1 of nieuwer**. Gebruik een Assist-pipeline met een beschikbare conversation-agent. Stel voor spraak zowel spraak-naar-tekst als tekst-naar-spraak in.

## Nodig

- Home Assistant. Voor Assist is geen apart gekoppeld apparaat nodig.
- Spotify Direct: Premium, je eigen Spotify Developer-app **Client ID** en een
  externe **HTTPS**-URL van HA. Nabu Casa is aanbevolen, niet verplicht.
- Music Assistant: geconfigureerd en een bruikbare speler; geen Spotify Client ID
  of Spotify OAuth via DJConnect. Met **Later / handmatig** stel je muziek later in.
- Koppel lokale apparaten op hetzelfde LAN; ESP32 gebruikt 2,4 GHz WiFi.

## Installeren en starten

1. Open DJConnect via de link hieronder of ga naar **Instellingen → Marktplaats → Toevoegen via link**. Vul `djconnect-music-dj/djconnect` in en kies zo nodig **Integratie**. Installeer DJConnect en herstart Home Assistant als daarom wordt gevraagd.
2. Open **Instellingen → Apparaten & diensten → Integratie toevoegen → DJConnect**.
3. Kies Assist, lokaal apparaat of app. Bluetooth kan optioneel alleen de WiFi
   van een ESP32 instellen; daarna volgt de koppeling.
4. Assist slaat koppelen over. Volg zo nodig de koppeling: iPhone/Watch via QR, macOS met de getoonde HA-URL
   en zescijferige code, ESP32/Pi lokaal. Gebruik een nieuwe code als de oude verloopt.
5. Kies of maak een **Profile**. Hergebruik behoudt de bestaande
   muziekverbinding. Een nieuw Profile kiest Spotify Direct, Music Assistant of Later.
6. Voor Spotify maak je een app in Spotify Developer Dashboard. Kopieer de **exacte
   redirect-URI uit de wizard** naar die app, vul de Client ID in (geen Client Secret)
   en rond de autorisatie af. Werk de URI bij en autoriseer opnieuw als de externe
   HA-URL verandert. Music Assistant vraagt alleen om zijn speler; Later stelt muziek uit.
7. Start een DJ-sessie in de gekoppelde client, of selecteer **DJConnect DJ** in Assist.
   Stel een uitgestelde muziekverbinding eerst in voordat je afspeelt.

## Hulp

Assist ontbreekt? Controleer de conversation-agent in je Assist-pipeline. Spotify keert niet
terug? Controleer de exacte redirect-URI. Koppeling mislukt? Controleer LAN en code.
Generiek HA-pictogram? Download opnieuw via de Marktplaats, herstart en ververs de frontend.

[DJConnect](https://my.home-assistant.io/redirect/marketplace_repository/?owner=djconnect-music-dj&repository=djconnect&category=integration) · [Repository](https://github.com/djconnect-music-dj/djconnect) · [English / en](installation.md)
