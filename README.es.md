<!-- The source is the Russian README.md; translations: README.<language>.md, the same structure. A change to README.md
     changes README.en.md in the same PR; the other languages follow (each says it was translated automatically from
     the Russian original and links it and Weblate). Pictures: docs/images/. -->
<div align="center">

# SMTV

**Convierte un stream largo en clips cortos y un resumen. Gratis, en tu propia computadora.**

<!-- languages -->
[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md) · [Oʻzbekcha](README.uz.md) · [Azərbaycanca](README.az.md) · [Кыргызча](README.ky.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [हिन्दी](README.hi.md) · [বাংলা](README.bn.md) · **Español** · [Português](README.pt-BR.md) · [Deutsch](README.de.md)

> 🌐 Esta página se tradujo automáticamente. Ayuda a mejorarla: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Original: Русский](README.md).

[![Última versión](https://img.shields.io/github/v/release/streammomenttv/smtv?label=release)](https://github.com/streammomenttv/smtv/releases/latest)
[![Descargas](https://img.shields.io/pepy/dt/smtv?label=downloads)](https://pepy.tech/projects/smtv)
[![Estrellas](https://img.shields.io/github/stars/streammomenttv/smtv?style=flat)](https://github.com/streammomenttv/smtv/stargazers)
[![Licencia: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/smtv)](https://pypi.org/project/smtv/)
[![Traducir en Weblate](https://hosted.weblate.org/widget/smtv/svg-badge.svg)](https://hosted.weblate.org/engage/smtv/)

<img src="docs/images/demo.gif" alt="SMTV: entra la grabación de un stream, SMTV encuentra los mejores momentos y hace clips verticales uno tras otro" width="820">

[**Descargar SMTV**](#descargar) · [Guías paso a paso](docs/guide/es/README.md) · [Comparación](#cómo-se-compara-smtv) · [Preguntas](#preguntas)

</div>

---

Hiciste un stream de seis horas. En algún lugar están los diez momentos que vale la pena publicar, pero encontrarlos
significa volver a verlo todo. **SMTV lo ve por ti.** Pega el enlace a una grabación de Twitch o YouTube, o elige un
archivo de video, y SMTV escucha todo el stream, elige los mejores momentos y te entrega **clips verticales listos
para publicar** en TikTok, Shorts y Reels, con subtítulos y la webcam arriba, además de **un resumen de 20–30 minutos**
de todo el stream para YouTube.

## Qué hace

| | |
|---|---|
| 🎬 **Clips listos para publicar** | Verticales 9:16, con subtítulos grandes, una breve tarjeta de título al inicio y la webcam del streamer encima del juego. |
| ⏱️ **Los streams largos no son problema** | Entra una grabación de 6–12 horas y salen hasta 30 clips. Los clips aparecen uno tras otro: empieza a publicar antes de que estén los demás. |
| 📺 **Un resumen de todo el stream** | Un video de 20–30 minutos para YouTube: el propio stream, recortado a las partes que vale la pena ver. |
| 🗣️ **Muchos idiomas** | Ruso, 25 idiomas europeos y decenas más. SMTV convierte la voz en texto directamente en tu computadora. |
| 🔒 **Tus archivos se quedan contigo** | Los clips se hacen y se guardan en tu computadora. No se sube nada a ningún sitio web. |
| 💸 **Gratis y abierto** | Licencia MIT: úsalo, compártelo, úsalo para clientes. Sin marca de agua, sin límite de minutos. |

## Míralo en acción

**Pega un enlace o elige un archivo, y mira los pasos.** Cada paso aparece en pantalla: voz a texto, búsqueda de
momentos, calificación, edición de cada clip.

<img src="docs/images/new-request.gif" alt="Una nueva solicitud: se elige un archivo de video, SMTV empieza y muestra cada paso" width="820">

**Los clips aparecen uno tras otro.** Míralos directamente en SMTV, descárgalos, publícalos.

<img src="docs/images/clips.png" alt="Clips terminados de un stream en una cuadrícula" width="820">

**Cada clip viene con su texto.** Lee lo que se dijo y por qué SMTV eligió ese momento.

<img src="docs/images/viewer.png" alt="Un clip reproduciéndose junto a su transcripción" width="820">

**Y un resumen de todo el stream** para YouTube, hecho después de los clips.

<img src="docs/images/recap.png" alt="El resumen del stream en SMTV" width="820">

**Claro u oscuro**, como en tu computadora.

<img src="docs/images/dark.png" alt="SMTV con el tema oscuro" width="820">

<sub>El stream de estas imágenes es inventado para la demo: un juego pequeño, una mascota animada en lugar de la webcam
y una voz de computadora. No aparece ninguna persona real en pantalla.</sub>

## Gratis y de código abierto

- **SMTV es gratis.** Todo el programa es de código abierto bajo la [licencia MIT](LICENSE): úsalo para ti, para tu
  canal o para clientes, modifícalo y compártelo.
- **Sin marca de agua, sin límite de minutos, sin suscripción a SMTV.**
- **Solo pagas por la IA, y solo si quieres.** SMTV necesita una IA para leer el texto del stream y elegir los
  momentos. Puede ser una IA gratuita en tu propia computadora o un servicio que tú elijas; mira más abajo.
- **Tus datos se quedan contigo.** Los clips se hacen y se guardan en tu computadora. Solo el texto del stream va a la
  IA que elegiste. Con una IA gratuita en tu computadora, no sale nada de ella.

## Elige tu IA: tres formas

SMTV convierte la voz en texto por sí mismo, en tu computadora. Para elegir los mejores momentos le pregunta a una IA.
Elige una forma (con una basta) y puedes cambiarla cuando quieras en **Settings → AI** (Configuración → IA).

| | Cómo | Costo | Ideal para |
|---|---|---|---|
| ⭐ **Con la cuenta** | Inicia sesión en una cuenta de StreamMoment (Google, Twitch o Telegram) y recarga el saldo. Eso es todo: sin claves, sin configuración. | Pagas lo que usas, desde el saldo | Todos: la forma más sencilla. También es necesaria para pegar **enlaces** a grabaciones. [Guía](docs/guide/es/account.md) |
| 🔑 **Tu propia clave** | ¿Ya usas OpenAI, Claude, Gemini u OpenRouter? Pega tu clave y SMTV la usa directamente. | Le pagas directamente a ese servicio; algunos tienen plan gratuito | Quienes ya usan un servicio de IA. [Dónde conseguir una clave](docs/guide/es/get-a-key.md) |
| 💻 **Gratis, en tu computadora** | Instala Ollama o LM Studio y un modelo Qwen; SMTV lo encuentra solo. | Gratis | Una computadora con una tarjeta gráfica potente. Los clips salen peores. [Guía](docs/guide/es/free-ai-on-your-computer.md) |

## Descargar

| Tu computadora | Descarga | Tamaño |
|---|---|---|
| **Windows 10 u 11** (64 bits) | [**SMTV para Windows**](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows-setup.exe) (instalador) | unos 130 MB |
| **Mac** — Apple silicon (M1 y posteriores) o Intel, macOS 13+ | [**SMTV para Mac**](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-mac.dmg) | unos 270 MB |

Un solo archivo para cualquier Mac: SMTV arranca por sí solo la versión hecha para el procesador de tu Mac. Windows sin instalar nada:
[el ZIP](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows.zip): descomprímelo y abre
**Start SMTV**.

Todo lo que SMTV necesita ya viene dentro: el programa, Python y ffmpeg con subtítulos. El reconocimiento de voz se
descarga en el primer inicio, solo para tu idioma (0,9–2,5 GB, una sola vez): SMTV lo ofrece con un botón, **Fix**
(Arreglar).

**La primera vez, el sistema te advierte.** SMTV todavía no tiene firma digital: la de Windows llegará un poco más
tarde, la de macOS lo antes posible, y entonces esta advertencia desaparecerá. Mientras tanto:

- **Windows** («Windows protegió su PC»): **Más información** (More info) → **Ejecutar de todas formas** (Run anyway).
- **Mac**: abre SMTV una vez y luego ve a **Ajustes del Sistema → Privacidad y seguridad** (System Settings → Privacy &
  Security) → **Abrir igualmente** (Open Anyway).
- **Windows 11 con Smart App Control** bloquea por completo los programas sin firma, y no hay ningún botón para dejarlos
  pasar. Usa la instalación en una línea de abajo: funciona con Smart App Control activado. Cuando SMTV esté firmado, la
  descarga también funcionará ahí.

[Cada paso, con imágenes](docs/guide/es/install.md).

### Para usuarios con experiencia: una línea en una terminal

El mismo SMTV, instalado con [uv](https://astral.sh/uv) en tu carpeta de usuario. También funciona en **Linux** y con
**Smart App Control**, y se actualiza desde la ventana igual que la descarga.

**Windows**: presiona Inicio, escribe **PowerShell**, ábrelo y pega:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.ps1 | iex"
```

**Mac o Linux**: abre **Terminal** y pega:

```bash
curl -LsSf https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.sh | sh
```

Presiona Enter y espera unos minutos. No hace falta contraseña de administrador. Aparece un ícono de **SMTV**: en el
escritorio y en el menú Inicio en Windows, en Aplicaciones en una Mac, en el menú de aplicaciones en Linux.

## Tu primer clip en tres pasos

1. **Elige una IA**: la primera vez, la ventana muestra las tres formas ([¿cuál?](docs/guide/es/connect-ai.md)).
2. **Pega un enlace** a una grabación de Twitch o YouTube, o elige un archivo de video de tu computadora.
3. **Espera.** Los clips aparecen uno tras otro: míralos, descárgalos, publícalos.

La primera vez, SMTV revisa tu computadora y ofrece arreglar lo que falte con un solo botón, **Fix** (Arreglar).
[El primer clip, paso a paso](docs/guide/es/first-clip.md).

## Guías paso a paso

Para quienes son nuevos en todo esto: cada paso, con imágenes.

| | |
|---|---|
| [Instalar en Windows, Mac o Linux](docs/guide/es/install.md) | y qué hacer cuando el sistema te advierte |
| [Tu primer clip](docs/guide/es/first-clip.md) | de un enlace o un archivo a un clip terminado |
| [Qué IA elegir](docs/guide/es/connect-ai.md) | las tres formas, lado a lado |
| [Una IA gratuita en tu computadora](docs/guide/es/free-ai-on-your-computer.md) | Ollama o LM Studio con Qwen: qué modelo va con tu tarjeta gráfica |
| [Dónde conseguir una clave](docs/guide/es/get-a-key.md) | qué servicios tienen un plan gratuito o barato, paso a paso |
| [La cuenta de StreamMoment](docs/guide/es/account.md) | iniciar sesión, saldo |
| [SMTV en tu teléfono](docs/guide/es/phone.md) | escanea un código QR y mira los clips en el teléfono |
| [Voz e idiomas](docs/guide/es/speech-and-languages.md) | qué idiomas entiende SMTV |
| [Actualizar y desinstalar](docs/guide/es/update-and-remove.md) | |
| [Algo salió mal](docs/guide/es/troubleshooting.md) | revisión de la computadora, **Fix**, **Report a problem** (Reportar un problema) |

## Cómo se compara SMTV

Los clippers de código abierto más usados, según el propio código y la documentación de cada proyecto, **a noviembre
de 2026**. Son buenos proyectos, cada uno hecho para su propia tarea; esta tabla solo muestra en qué se diferencia
SMTV. ¿Algo cambió? [Avísanos](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml) y corregiremos la
tabla.

| | **SMTV** | [openshorts](https://github.com/mutonby/openshorts) | [SupoClip](https://github.com/FujiwaraChoki/supoclip) | [PeakCut](https://github.com/haziqahmedqasmi/PeakCut) | [FunClip](https://github.com/modelscope/FunClip) |
|---|---|---|---|---|---|
| Licencia | **MIT** | MIT (la carpeta `cloud/` tiene su propia licencia) | Licencia de código fuente no comercial | MIT | MIT |
| Un stream completo de 6–12 horas | **Sí** | 60 minutos por tarea por defecto | 90 minutos por defecto | No indica límite de duración | No está hecho para streams |
| Un resumen largo de todo el stream | **Sí, 20–30 minutos** | No | No (su «recap» es un solo clip corto) | No | No |
| Voz en ruso | **GigaAM-v3, hecho para el ruso** | Whisper o Parakeet v3 | AssemblyAI o Whisper | No (Parakeet v2, solo inglés) | No (chino e inglés) |
| Webcam del streamer en el cuadro vertical | **Sí** | No | Modo gaming, desactivado por defecto | Sí | No hace clips verticales |
| Voz a texto por defecto | **En tu computadora, gratis** | En tu computadora | AssemblyAI, un servicio de pago | En tu computadora | En tu computadora |
| Cómo se abre | **Ventana e ícono propios: descarga para Windows y Mac, o una línea** | Página web en Docker | Página web en Docker | Página web | Página web |

## Preguntas

<details>
<summary><b>¿De verdad es gratis?</b></summary>

Sí. SMTV en sí no cuesta nada y no tiene límites. El único costo posible es la IA que elige los momentos: gratis en tu
propia computadora, o pagada al servicio que elijas (a través de la cuenta de StreamMoment o de tu propia clave).
</details>

<details>
<summary><b>¿Necesito una computadora potente?</b></summary>

No hace falta tarjeta gráfica: SMTV funciona en una computadora común, solo que más lento. Una tarjeta NVIDIA acelera la
conversión de voz a texto. La excepción es una IA gratuita en tu propia computadora: necesita una tarjeta gráfica
potente ([cuál](docs/guide/es/free-ai-on-your-computer.md)). Espacio libre en disco: 5 GB como mínimo, 20 GB para un
stream de 6 horas.
</details>

<details>
<summary><b>¿Cuánto tarda?</b></summary>

Medido en una Mac con Apple silicon, sin tarjeta gráfica: una grabación de Twitch de 2.35 horas tardó unos 6 minutos en
encontrar los momentos y luego alrededor de 1 minuto por clip; un resumen de 10.7 minutos tardó 6.5 minutos. Antes de
que empiece una solicitud, SMTV muestra cuánto debería tardar.
</details>

<details>
<summary><b>¿En qué sistemas funciona?</b></summary>

Windows 10 (versión 1809) o posterior, de 64 bits; macOS 13 o posterior en Apple silicon e Intel (en Apple silicon SMTV funciona de forma nativa desde macOS 14; en macOS 13 ejecuta su versión para Intel a través de Rosetta, más lenta); Linux (instalación en una línea). Probado en Windows 11 y en Macs con Apple silicon; las Macs con Intel (solo
bajo Rosetta) y los escritorios Linux aún no se han probado.
</details>

<details>
<summary><b>¿Qué idiomas entiende?</b></summary>

Ruso, 25 idiomas europeos y decenas más. SMTV detecta el idioma del stream por sí mismo.
[Detalles](docs/guide/es/speech-and-languages.md).
</details>

<details>
<summary><b>¿Puedo usar los clips para mis clientes?</b></summary>

Sí. La licencia MIT permite cualquier uso, incluido el comercial: hacer clips para streamers, agencias o tus propios
canales. Respeta los derechos del streamer cuyo stream recortas.
</details>

<details>
<summary><b>¿Dónde quedan mis clips? ¿Se sube algo?</b></summary>

Los clips se quedan en tu computadora. Un archivo de video tuyo nunca sale de ella. Un enlace se descarga a través de
la cuenta de StreamMoment: su servidor le pasa la grabación a SMTV por partes y no guarda nada. El texto del stream va
solo a la IA que elegiste. Las claves de los servicios de IA se quedan en tu computadora y nunca aparecen en registros
ni en reportes de problemas.
</details>

<details>
<summary><b>¿Publica en TikTok o YouTube por sí solo?</b></summary>

Todavía no: descargas los clips y los publicas tú. Settings → About → «Coming» (Configuración → Acerca de → Próximamente)
muestra lo que está planeado.
</details>

<details>
<summary><b>Algo no funciona.</b></summary>

Settings → **Computer check** → **Fix** (Configuración → Revisión de la computadora → Arreglar) resuelve la mayoría de
los problemas. ¿Sigues atorado? Settings → Computer check → **Report…** (Reportar…): SMTV prepara un reporte sin tus
claves y abre una página en GitHub; no se envía nada por sí solo.
[Qué probar](docs/guide/es/troubleshooting.md).
</details>

## Ayuda a traducir SMTV

La ventana de SMTV habla el idioma de tu computadora. Las traducciones las hacen personas en
[Weblate](https://hosted.weblate.org/engage/smtv/), sin necesidad de programar: abre la página, elige tu idioma,
traduce unas cuantas líneas. Las traducciones de esta página se hicieron automáticamente; si ves un error, corrígelo
en un pull request. [Cómo funcionan las traducciones](docs/translations.md).

[![Estado de la traducción](https://hosted.weblate.org/widget/smtv/multi-auto.svg)](https://hosted.weblate.org/engage/smtv/)

## StreamMoment

SMTV lo hace el equipo de [StreamMoment](https://streammoment.tv). La cuenta de StreamMoment es la forma más sencilla de
darle una IA a SMTV y de pegar enlaces a grabaciones; SMTV también funciona sin ella.

- [Reportar un problema](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml) · [Proponer una idea](https://github.com/streammomenttv/smtv/issues/new?template=feature.yml)
- [Para usuarios avanzados](docs/advanced.md): Docker, todos los servicios de IA, modelos de voz, claves, comandos
- [Cambios](CHANGELOG.md) · [Cómo contribuir](CONTRIBUTING.md) · [Seguridad](SECURITY.md)
- ¿Te gusta SMTV? [Apóyalo en Boosty](https://boosty.to/smtv) y dale una ⭐ al repositorio: ayuda a que otros lo encuentren.

Licencia: [MIT](LICENSE).
