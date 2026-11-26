<!-- languages -->
[Русский](../troubleshooting.md) · [English](../en/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · [한국어](../ko/troubleshooting.md) · [Tiếng Việt](../vi/troubleshooting.md) · [Bahasa Indonesia](../id/troubleshooting.md) · [हिन्दी](../hi/troubleshooting.md) · [বাংলা](../bn/troubleshooting.md) · **Español** · [Português](../pt-BR/troubleshooting.md) · [Deutsch](../de/troubleshooting.md)

> 🌐 Esta página se tradujo automáticamente. Ayuda a mejorarla: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Original: Русский](../troubleshooting.md).

# Algo salió mal

## 1. Revisión de la computadora → Fix

**Settings → Computer check** (Configuración → Revisión de la computadora) revisa todo lo que SMTV necesita y dice,
línea por línea, qué está bien y qué no. Junto a cada problema hay un botón **Fix** (Arreglar): SMTV instala o repara
por sí solo lo que puede y muestra lo que hace.

<img src="../../images/check.png" alt="Settings → Computer check: cada línea con su estado y un botón Fix" width="820">

| La línea dice | Qué hacer |
|---|---|
| Falta **Video (ffmpeg)** | Presiona **Fix**: SMTV instala ffmpeg, la herramienta de video que usa. |
| **Captions** (Subtítulos) no funcionan | Presiona **Fix**: SMTV instala un ffmpeg que puede dibujar subtítulos. |
| **AI**: no hay nada conectado | Elige una en **Settings → AI**: [cuál](connect-ai.md). |
| **Connection to StreamMoment** (Conexión con StreamMoment) falla | Revisa el internet; una VPN o un firewall podrían bloquearla. Los archivos siguen funcionando sin ella. |
| Hay poco **Free space** (Espacio libre) | Libera espacio en disco: un stream de 6 horas necesita unos 20 GB mientras se procesa. |
| **Speech to text** (Voz a texto): un modelo no está descargado | Se descarga solo en la primera solicitud; o presiona **Download** en **Settings → Speech to text**. |

Un arreglo que necesita contraseña de administrador nunca se ejecuta en silencio: SMTV abre una terminal con el
comando, para que veas lo que hace.

## 2. Problemas comunes

- **Un enlace no funciona.** Los enlaces necesitan la [cuenta de StreamMoment](account.md). ¿No tienes cuenta? Descarga
  la grabación tú mismo y dale el archivo a SMTV.
- **No hay clips, o hay muy pocos.** SMTV solo conserva los momentos que la IA calificó como buenos. Un stream corto o
  tranquilo puede dar pocos. Una IA gratuita en tu computadora encuentra menos momentos buenos que una en la nube.
- **«Too many requests»** (Demasiadas solicitudes). El plan gratuito de tu servicio de IA llegó a su límite: espera, o
  usa un plan de pago o la cuenta.
- **El teléfono no abre SMTV.** Misma Wi-Fi, sin VPN, permite SMTV en el firewall: mira [teléfono](phone.md).
- **Windows: una terminal rechaza `smtv`.** Es Smart App Control; abre SMTV desde su ícono.
- **La ventana perdió la conexión con SMTV.** Cierra la ventana y vuelve a abrir SMTV.

Una solicitud que se detuvo puede continuar: presiona **Continue** (Continuar). SMTV retoma desde el mismo paso y no
rehace lo que ya está hecho.

## 3. Reportar un problema

¿Sigues atorado? Cuéntanos: ayuda a todos.

1. **Settings → Computer check → Report a problem** (Configuración → Revisión de la computadora → Reportar un problema;
   el botón **Report…**, que también está en **Settings → About**), o el botón debajo de una solicitud que falló.
2. SMTV muestra lo que va en el reporte: versiones, la revisión de la computadora, la configuración y los registros.
   **Las claves y los tokens se eliminan**, tu carpeta personal aparece como `~`. Los enlaces y los nombres de archivo
   quedan fuera a menos que marques la casilla.
3. Presiona **Save and open GitHub** (Guardar y abrir GitHub). SMTV guarda el archivo comprimido y se abre un nuevo issue
   en el navegador con el resumen ya escrito. Arrastra el archivo comprimido ahí y presiona **Submit**.

SMTV no envía nada por sí solo. Sin la ventana: ejecuta `smtv report` en una terminal. También puedes
[abrir un issue](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml) directamente.
