# Instalar DJConnect

**Your music. Your DJ.**

Tu DJ musical personal en Home Assistant. Pide música, disfruta de las intervenciones del DJ y elige el ambiente de tu sesión.

## Antes de empezar

DJConnect **4.0.0** requiere Home Assistant **2026.11.1 o posterior**. Usa una canalización de Assist con un agente de conversación disponible. Para el uso por voz, configura el reconocimiento y la síntesis de voz.

## Requisitos

- Home Assistant; Assist no necesita otro dispositivo emparejado.
- Spotify Direct: Premium, el **Client ID** de tu propia aplicación Spotify
  Developer y una URL externa de HA **HTTPS**. Nabu Casa es recomendable, no obligatorio.
- Music Assistant: instalación configurada y reproductor utilizable, sin Client ID
  de Spotify ni OAuth Spotify en DJConnect. **Later / manual** permite configurar la música más tarde.
- Empareja los dispositivos locales en la misma LAN; ESP32 usa WiFi de 2,4 GHz.

## Instalar e iniciar

1. Abre DJConnect con el enlace de abajo o desde **Ajustes → Marketplace → Añadir desde un enlace**. Introduce `pcvantol/djconnect` y selecciona **Integración** si se solicita. Instala DJConnect y reinicia Home Assistant si se indica.
2. Abre **Ajustes → Dispositivos y servicios → Añadir integración → DJConnect**.
3. Elige Assist, dispositivo local o aplicación. Bluetooth solo configura, si hace
   falta, el WiFi de un ESP32; después se realiza el emparejamiento.
4. Assist omite el emparejamiento. Si procede: iPhone/Watch por QR, macOS con la URL HA y el código de seis cifras
   indicados, ESP32/Pi en la red local. Renueva los códigos caducados.
5. Elige o crea un **Profile**. Reutilizarlo conserva su conexión
   musical. Un Profile nuevo elige Spotify Direct, Music Assistant o Later.
6. Para Spotify crea una aplicación en Spotify Developer Dashboard. Copia la **URI
   exacta de redirección del asistente** allí, introduce el Client ID (no Client Secret)
   y termina la autorización. Si cambia la URL externa de HA, actualiza la URI y
   autoriza de nuevo. Music Assistant pide su reproductor; Later aplaza la conexión musical.
7. Inicia una sesión DJ en el cliente conectado o selecciona **DJConnect DJ** en Assist.
   Configura cualquier conexión musical aplazada antes de reproducir.

## Ayuda

Si falta Assist, comprueba el agente de conversación de tu canalización de Assist. Si Spotify no vuelve,
comprueba la URI exacta. Si falla el emparejamiento, comprueba LAN y código. Si el
icono de HA es genérico, vuelve a descargar desde Marketplace, reinicia HA y actualiza la interfaz.

[DJConnect](https://my.home-assistant.io/redirect/marketplace_repository/?owner=pcvantol&repository=djconnect&category=integration) · [Repository](https://github.com/pcvantol/djconnect) · [English / en](installation.md)
