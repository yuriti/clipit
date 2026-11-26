<!-- languages -->
[Русский](../update-and-remove.md) · [English](../en/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · **Español** · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 Esta página se tradujo automáticamente. Ayuda a mejorarla: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Original: Русский](../update-and-remove.md).

# Actualizar y desinstalar

## Actualizar

SMTV busca una versión nueva una vez al día (puedes desactivarlo). Cuando hay una, dice **Version … is available**
(La versión … está disponible): presiona **Update** (Actualizar).

- SMTV se cierra, se actualiza y se vuelve a abrir solo, normalmente en menos de un minuto.
- Si hay una solicitud en curso, la actualización espera a que termine; o presiona **Stop the jobs and update**
  (Detener los trabajos y actualizar), y después **Continue** los retoma desde el mismo paso.
- Si la versión nueva no arranca, la anterior vuelve sola.
- Las versiones nuevas están firmadas por los autores de SMTV; SMTV comprueba la firma antes de instalar.

Todo lo relacionado con las actualizaciones está en **Settings → Computer check → Updates** (Configuración → Revisión
de la computadora → Actualizaciones).

¿Descargaste SMTV para Windows o Mac? **Update** (Actualizar) descarga el instalador nuevo, lo comprueba y lo abre:
termina la instalación ahí (en una Mac, arrastra el SMTV nuevo sobre Aplicaciones y presiona **Reemplazar** (Replace)).
La copia de Windows desde el ZIP no se actualiza sola: descarga el ZIP nuevo desde [la página de la versión](https://github.com/yuriti/clipit/releases/latest).

¿Instalaste SMTV de otra forma? En Docker, una versión nueva es una imagen nueva; mira [para usuarios avanzados](../../advanced.md#docker).

## Desinstalar

**Settings → Computer check → Remove SMTV from this computer** (Quitar SMTV de esta computadora; el botón **Remove…**)
quita el programa y el ícono de SMTV. Tus clips se quedan; marca **Also remove clips, jobs, settings and keys** (Quitar
también clips, trabajos, configuración y claves) para quitarlos también.

¿Descargaste SMTV para Windows o Mac? Desinstala el programa en sí a la manera del sistema (el botón de arriba quita
solo los clips y la configuración, si los marcas):

- **Windows:** **Configuración → Aplicaciones → Aplicaciones instaladas → SMTV → Desinstalar** (Settings → Apps →
  Installed apps → SMTV → Uninstall). La copia desde el ZIP: borra su carpeta.
- **Mac:** arrastra **SMTV** desde **Aplicaciones** (Applications) a la **Papelera** (Trash).

¿Lo instalaste con una línea en una terminal? Sin la ventana, en una terminal:

```bash
smtv uninstall
```

Agrega `--data` para quitar también los clips y la configuración. Los programas que instalaste tú (Ollama, LM Studio) se
quedan: desinstálalos como cualquier otro programa.
