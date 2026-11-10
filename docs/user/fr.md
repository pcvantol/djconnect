# Installer DJConnect

**Your music. Your DJ.**

Votre DJ musical personnel dans Home Assistant. Demandez de la musique, profitez des interventions du DJ et choisissez l’ambiance de votre session.

## Choisir la version

Ce guide concerne DJConnect **4.0.0**. Utilisez un pipeline Assist avec un agent de conversation disponible. La voix est facultative pendant la configuration.

## Prérequis

- Home Assistant ; Assist ne nécessite pas d’appareil couplé séparément.
- Spotify Direct : Premium, le **Client ID** de votre propre application Spotify
  Developer et une URL HA externe **HTTPS**. Nabu Casa est recommandé, sans être obligatoire.
- Music Assistant : installation configurée et lecteur utilisable, sans Client ID
  Spotify ni OAuth Spotify dans DJConnect. **Later / manual** reporte la configuration musicale.
- Coupler les appareils locaux sur le même LAN ; ESP32 utilise le WiFi 2,4 GHz.

## Installer et démarrer

1. Ouvrez DJConnect avec le lien ci-dessous ou via **Paramètres → Marketplace → Ajouter depuis un lien**. Saisissez `pcvantol/djconnect` et sélectionnez **Intégration** si nécessaire. Installez DJConnect, puis redémarrez Home Assistant si l’interface le demande.
2. Ouvrez **Paramètres → Appareils et services → Ajouter une intégration → DJConnect**.
3. Choisissez Assist, appareil local ou application. Bluetooth configure uniquement
   le WiFi d’un ESP32, si nécessaire ; le couplage vient ensuite.
4. Assist ignore le couplage. Si nécessaire : iPhone/Watch par QR, macOS avec l’URL HA et le code à six chiffres
   affichés, ESP32/Pi localement. Renouvelez un code expiré.
5. En 4.0, choisissez ou créez d’abord un **Profile**. La réutilisation conserve sa
   connexion musicale. Un nouveau Profile choisit Spotify Direct, Music Assistant ou Later.
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
téléchargez à nouveau via le Marketplace, redémarrez HA et actualisez l’interface.

[DJConnect](https://my.home-assistant.io/redirect/marketplace_repository/?owner=pcvantol&repository=djconnect&category=integration) · [Repository](https://github.com/pcvantol/djconnect) · [English / en](installation.md)
