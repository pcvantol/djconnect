# Instalar DJConnect

**Your music. Your DJ.**

Tu DJ musical personal en Home Assistant. Pide música, disfruta de las intervenciones del DJ y elige el ambiente de tu sesión.

## Elegir la versión

Esta fuente describe el candidato **4.0.0-rc.1**, no una versión instalada.
Comprueba la versión en HACS. **3.3.1** requiere un pipeline Assist con **STT y TTS**.
El candidato necesita un agente de conversación disponible; la voz es opcional
para la configuración. Solo se ofrecen las rutas de voz disponibles.

## Requisitos

- Home Assistant y HACS; Assist no necesita otro dispositivo emparejado.
- Spotify Direct: Premium, el **Client ID** de tu propia aplicación Spotify
  Developer y una URL externa de HA **HTTPS**. Nabu Casa es recomendable, no obligatorio.
- Music Assistant: instalación configurada y reproductor utilizable, sin Client ID
  de Spotify ni OAuth Spotify en DJConnect. **Later / manual** existe en ambas versiones.
- Empareja los dispositivos locales en la misma LAN; ESP32 usa WiFi de 2,4 GHz.

## Instalar e iniciar

1. Abre el enlace HACS inferior o añade el repositorio como **Integration** en
   **Repositorios personalizados**. Instala DJConnect y reinicia HA.
2. Abre **Ajustes → Dispositivos y servicios → Añadir integración → DJConnect**.
3. Elige Assist, dispositivo local o aplicación. Bluetooth solo configura, si hace
   falta, el WiFi de un ESP32; después se realiza el emparejamiento.
4. Assist omite el emparejamiento. Si procede: iPhone/Watch por QR, macOS con la URL HA y el código de seis cifras
   indicados, ESP32/Pi en la red local. Renueva los códigos caducados.
5. En 4.0 elige o crea primero un **Profile**. Reutilizarlo conserva su conexión
   musical. Un Profile nuevo elige Spotify Direct, Music Assistant o Later.
   En 3.3.1 primero se elige el backend y después se crea un Profile nuevo.
6. Para Spotify crea una aplicación en Spotify Developer Dashboard. Copia la **URI
   exacta de redirección del asistente** allí, introduce el Client ID (no Client Secret)
   y termina la autorización. Si cambia la URL externa de HA, actualiza la URI y
   autoriza de nuevo. Music Assistant pide su reproductor; Later aplaza la conexión musical.
7. Inicia una sesión DJ en el cliente conectado o selecciona **DJConnect DJ** en Assist.
   Configura cualquier conexión musical aplazada antes de reproducir.

## Ayuda

Si falta Assist, comprueba los requisitos de tu versión. Si Spotify no vuelve,
comprueba la URI exacta. Si falla el emparejamiento, comprueba LAN y código. Si el
icono de HA es genérico, vuelve a descargar en HACS, reinicia HA y actualiza la interfaz.

[HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=pcvantol&repository=djconnect&category=integration) · [Repository](https://github.com/pcvantol/djconnect) · [English / en](installation.md)
