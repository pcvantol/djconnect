# Installer DJConnect

**Your music. Your DJ.**

Votre DJ musical personnel dans Home Assistant. Demandez de la musique, profitez des interventions du DJ et choisissez l’ambiance de votre session.

## Choisir la version

Cette source décrit le candidat **4.0.0-rc.1**, pas une version installée.
Vérifiez la version dans HACS. **3.3.1** exige un pipeline Assist avec **STT et TTS**.
Le candidat exige un agent de conversation disponible ; la voix est optionnelle
pour la configuration. Seuls les parcours vocaux disponibles sont proposés.

## Prérequis

- Home Assistant et HACS ; Assist ne nécessite pas d’appareil couplé séparément.
- Spotify Direct : Premium, le **Client ID** de votre propre application Spotify
  Developer et une URL HA externe **HTTPS**. Nabu Casa est recommandé, sans être obligatoire.
- Music Assistant : installation configurée et lecteur utilisable, sans Client ID
  Spotify ni OAuth Spotify dans DJConnect. **Later / manual** existe dans les deux versions.
- Coupler les appareils locaux sur le même LAN ; ESP32 utilise le WiFi 2,4 GHz.

## Installer et démarrer

1. Ouvrez le lien HACS ci-dessous ou ajoutez le dépôt comme **Integration** dans
   **Dépôts personnalisés**. Installez DJConnect puis redémarrez HA.
2. Ouvrez **Paramètres → Appareils et services → Ajouter une intégration → DJConnect**.
3. Choisissez Assist, appareil local ou application. Bluetooth configure uniquement
   le WiFi d’un ESP32, si nécessaire ; le couplage vient ensuite.
4. Assist ignore le couplage. Si nécessaire : iPhone/Watch par QR, macOS avec l’URL HA et le code à six chiffres
   affichés, ESP32/Pi localement. Renouvelez un code expiré.
5. En 4.0, choisissez ou créez d’abord un **Profile**. La réutilisation conserve sa
   connexion musicale. Un nouveau Profile choisit Spotify Direct, Music Assistant ou Later.
   En 3.3.1, choisissez d’abord le backend, puis créez un nouveau Profile.
6. Pour Spotify, créez une application dans Spotify Developer Dashboard. Copiez
   l’**URI de redirection exacte du guide de configuration** dans cette application,
   saisissez le Client ID (pas de Client Secret) et autorisez Spotify. Si l’URL HA
   externe change, actualisez l’URI et autorisez de nouveau. Music Assistant demande
   son lecteur ; Later reporte la connexion musicale.
7. Démarrez une session DJ dans le client connecté ou sélectionnez **DJConnect DJ**
   dans Assist. Configurez une connexion musicale reportée avant la lecture.

## Aide

Assist absent : vérifiez les prérequis de votre version. Spotify ne revient pas :
vérifiez l’URI exacte. Échec de couplage : vérifiez LAN et code. Icône HA générique :
téléchargez de nouveau dans HACS, redémarrez HA et actualisez l’interface.

[HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration) · [Repository](https://github.com/pcvantol/djconnect) · [English / en](installation.md)
