<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · **Español** · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 Esta página se tradujo automáticamente. Ayuda a mejorarla: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Original: Русский](../install.md).

# Instalar SMTV

Descarga un archivo, ábrelo y aparece un ícono de **SMTV**. Todo lo que SMTV necesita ya viene dentro. No necesitas
contraseña de administrador.

| Tu computadora | Descarga | Tamaño |
|---|---|---|
| **Windows 10 u 11** (64 bits) | [SMTV para Windows](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip) | unos 130 MB |
| **Mac** — Apple silicon (M1 y posteriores) o Intel, macOS 13+ | [SMTV para Mac](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | unos 270 MB |

Todas las versiones y sus sumas de verificación: [la página de la versión](https://github.com/yuriti/clipit/releases/latest).

**Por qué el sistema te advierte la primera vez.** SMTV todavía no tiene firma digital. La firma para Windows llegará
un poco más tarde, la de macOS lo antes posible, y entonces esta advertencia desaparecerá. El código de SMTV es abierto:
cualquiera puede leer lo que hace.

## Windows

1. Descarga **SMTV para Windows** (el archivo `SMTV-…-windows-x64-setup.exe`) y ábrelo.
2. Windows muestra una ventana azul **«Windows protegió su PC»** («Windows protected your PC»). Presiona **Más
   información** (More info) y luego **Ejecutar de todas formas** (Run anyway).
3. El instalador hace un par de preguntas (idioma, un ícono en el escritorio): presiona **Siguiente** (Next) e
   **Instalar** (Install).
4. Al final deja marcado **Iniciar SMTV** (Launch SMTV) y presiona **Finalizar** (Finish). La próxima vez abre SMTV
   desde el menú **Inicio** (o desde el ícono del escritorio).

El instalador pone SMTV en tu propia carpeta de usuario; aparece en **Configuración → Aplicaciones** (Settings → Apps),
donde puedes desinstalarlo.

**Sin instalar:** descarga [el ZIP](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip),
descomprímelo donde quieras (por ejemplo, en Documentos) y abre **SMTV.exe** en la carpeta `SMTV`. Esta copia no se
actualiza sola: una versión nueva es un ZIP nuevo.

### Windows 11: Smart App Control

Si **Smart App Control** está activado (Seguridad de Windows → Control de aplicaciones y navegador), Windows bloquea por
completo los programas sin firma, y no hay ningún botón para dejarlos pasar. No tienes que desactivar Smart App Control
para SMTV. En su lugar, instala SMTV con una línea; funciona con Smart App Control activado: [una línea en una terminal](#para-usuarios-con-experiencia-una-línea-en-una-terminal).
Cuando SMTV esté firmado, la descarga también funcionará ahí.

## Mac

1. Descarga **SMTV para Mac**. Es un solo archivo para cualquier Mac, con Apple silicon o Intel: SMTV arranca por sí solo la versión hecha para el procesador de tu Mac.
2. Abre el `.dmg` descargado. Se abre una ventana con SMTV y la carpeta **Aplicaciones** (Applications): arrastra
   **SMTV** sobre **Aplicaciones**.
3. Abre **Aplicaciones** y haz doble clic en **SMTV**. macOS dice que no puede verificar SMTV y no lo abre. Presiona
   **OK** (Done).
4. Abre **Ajustes del Sistema → Privacidad y seguridad** (System Settings → Privacy & Security) y desplázate hacia
   abajo. Junto a «Se ha bloqueado SMTV…» presiona **Abrir igualmente** (Open Anyway), escribe la contraseña de tu Mac
   y presiona **Abrir** (Open).
   En macOS 14 hay un camino más corto: clic derecho en **SMTV** en Aplicaciones → **Abrir** → **Abrir**.

Solo la primera vez: después SMTV se abre con un clic normal, desde Aplicaciones o Launchpad. Los mismos pasos están en
el archivo «How to open» dentro del `.dmg`.

## El primer inicio

SMTV revisa tu computadora y muestra tres pasos hasta el primer clip. Debajo ofrece el **reconocimiento de voz para tu
idioma**: la parte que convierte lo que se habla en el stream en texto. No viene dentro de la descarga, porque cada
idioma necesita el suyo (0,9–2,5 GB). Presiona **Fix** (Arreglar) y mira el avance, o sáltalo: la primera solicitud lo
descarga sola.

**Qué necesitas:** 5 GB de espacio libre como mínimo, 20 GB para un stream de 6 horas; internet. No hace falta tarjeta
gráfica.

## Para usuarios con experiencia: una línea en una terminal

El mismo SMTV, instalado con [uv](https://astral.sh/uv) (una pequeña herramienta oficial para programas de Python) en
tu carpeta de usuario. Úsalo en **Linux**, con **Smart App Control** o si prefieres una terminal. Se actualiza desde la
ventana igual que la aplicación descargada.

**Windows:** presiona **Inicio**, escribe `PowerShell`, abre **Windows PowerShell** (la ventana azul), pega esta línea
(clic derecho o Ctrl+V) y presiona **Enter**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

Con Smart App Control activado, el instalador pone SMTV sobre el Python firmado de python.org (puede pedirte
instalarlo: acepta) y abre SMTV a través de él. Si una terminal dice que no puede ejecutar `smtv`, usa el ícono de
**SMTV**.

**Mac o Linux:** abre **Terminal** (en una Mac: Cmd+Espacio, escribe `Terminal`, Enter), pega esta línea y presiona
**Enter**:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

Espera hasta que diga que terminó (de 2 a 10 minutos). SMTV se abre solo; el ícono de **SMTV** está en el menú Inicio en
Windows, en Aplicaciones en una Mac, en el menú de aplicaciones en Linux. Por este camino, la primera vez SMTV ofrece
instalar **ffmpeg** (la herramienta de video) con **Fix**; la descarga de arriba ya lo trae dentro.

Los dos instaladores son cortos y abiertos: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## Si el sistema te advierte

- **Windows: «Windows protegió su PC»** («Windows protected your PC», SmartScreen). Presiona **Más información** (More
  info) y luego **Ejecutar de todas formas** (Run anyway).
- **Windows 11: Smart App Control bloquea SMTV.** Usa [una línea en una terminal](#para-usuarios-con-experiencia-una-línea-en-una-terminal)
  hasta que SMTV esté firmado.
- **Windows: el firewall pregunta** si SMTV puede usar la red. Permítelo para redes **privadas**: SMTV lo necesita para
  abrirse en tu teléfono. Decir que no está bien si no necesitas el teléfono.
- **Mac: «No se puede abrir SMTV»** («SMTV cannot be opened»), «Apple no ha podido verificar…» o «no se puede verificar
  el desarrollador». Abre **Ajustes del Sistema → Privacidad y seguridad** (System Settings → Privacy & Security),
  desplázate hacia abajo y presiona **Abrir igualmente** (Open Anyway) junto a SMTV.
- **Mac: «¿Quieres que SMTV acepte conexiones entrantes?»** («SMTV would like to accept incoming connections»):
  permítelo si quieres usar SMTV en tu teléfono.
- ¿El **antivirus** se queja? SMTV es nuevo y todavía no está firmado, así que algunos antivirus lo tratan con cuidado.
  Su código es abierto, y las sumas de verificación de cada archivo están en [la página de la versión](https://github.com/yuriti/clipit/releases/latest)
  (`SHA256SUMS.txt`).

Siguiente: [tu primer clip](first-clip.md).
