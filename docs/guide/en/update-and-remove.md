<!-- languages -->
[Русский](../update-and-remove.md) · **English** · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 This page was translated automatically from the [Russian original](../update-and-remove.md). Help improve it: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls).

# Update and remove

## Update

Clip It! checks for a new version once a day (you can turn this off). When there is one, it says **Version … is
available**: press **Update**.

- Clip It! closes, updates and opens again by itself, usually within a minute.
- If a request is running, the update waits until it ends — or press **Stop the jobs and update**; **Continue** goes
  on with them from the same step afterwards.
- If the new version does not start, the previous one comes back by itself.
- New versions are signed by Clip It!'s authors; Clip It! checks the signature before installing.

Everything about updates is in **Settings → Computer check → Updates**.

Downloaded Clip It! for Windows? **Update** downloads the new version, checks it and replaces the program in the same
folder: your settings, models and clips stay. On a Mac **Update** downloads and opens the new disk image: drag the new
Clip It! onto Applications and press **Replace**.

Installed Clip It! in another way? In Docker a new version is a new image; see [for advanced users](../../advanced.md#docker).

## Remove

**Settings → Computer check → Remove Clip It! from this computer** (the **Remove…** button) removes the program and the Clip It! icon. Your clips stay — tick
**Also remove clips, jobs, settings and keys** to remove them too.

- **Windows:** everything is in the `ClipIt` folder. The button above removes the program from it right after Clip It!
  closes, and with the tick your settings and clips too. You can also just delete the whole folder. The earlier version
  with an installer (SMTV) goes in **Settings → Apps → Installed apps → SMTV → Uninstall**.
- **Mac:** remove the program the system's way: drag **Clip It!** from **Applications** to the **Trash** (the button
  above removes only the clips and settings, if you tick them).

Installed with one line in a terminal? Without the window, in a terminal:

```bash
smtv uninstall
```

Add `--data` to remove the clips and settings too. Programs you installed yourself (Ollama, LM Studio) stay: remove
them like any other program.
