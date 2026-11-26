<!-- languages -->
[Русский](../troubleshooting.md) · **English** · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · [한국어](../ko/troubleshooting.md) · [Tiếng Việt](../vi/troubleshooting.md) · [Bahasa Indonesia](../id/troubleshooting.md) · [हिन्दी](../hi/troubleshooting.md) · [বাংলা](../bn/troubleshooting.md) · [Español](../es/troubleshooting.md) · [Português](../pt-BR/troubleshooting.md) · [Deutsch](../de/troubleshooting.md)

> 🌐 This page was translated automatically from the [Russian original](../troubleshooting.md). Help improve it: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# Something went wrong

## 1. Computer check → Fix

**Settings → Computer check** looks at everything SMTV needs and says, line by line, what is fine and what is not.
Next to a problem there is a **Fix** button: SMTV installs or repairs what it can by itself and shows what it does.

<img src="../../images/check.png" alt="Settings → Computer check: every line with its state and a Fix button" width="820">

| The line says | What to do |
|---|---|
| **Video (ffmpeg)** is missing | Press **Fix**: SMTV installs ffmpeg, the video tool it uses. |
| **Captions** do not work | Press **Fix**: SMTV installs an ffmpeg that can draw captions. |
| **AI**: nothing connected | Choose one in **Settings → AI** — [which one](connect-ai.md). |
| **Connection to StreamMoment** fails | Check the internet; a VPN or a firewall may block it. Files still work without it. |
| **Free space** is low | Free some disk space: a 6-hour stream needs about 20 GB while it is processed. |
| **Speech to text**: a model is not downloaded | It downloads by itself at the first request; or press **Download** in **Settings → Speech to text**. |

A fix that needs an administrator password is never run silently: SMTV opens a terminal with the command, so you see
what it does.

## 2. Common problems

- **A link does not work.** Turn on **Download links myself** in **Settings → VodCut**, then press **Fix** next to
  yt-dlp in **Settings → Computer check** (links through the [StreamMoment account](account.md) are coming soon).
  Still no luck? Download the recording yourself and give SMTV the file.
- **No clips, or very few.** SMTV keeps only the moments the AI rated as good. A short or quiet stream may give few. A
  free AI on your computer finds fewer good moments than a cloud one.
- **«Too many requests».** The free plan of your AI service hit its limit: wait, or use a paid plan.
- **The phone does not open SMTV.** Same Wi-Fi, no VPN, allow SMTV in the firewall — see [phone](phone.md).
- **Windows: a terminal refuses `smtv`.** That is Smart App Control; start SMTV from its icon.
- **The window lost its connection to SMTV.** Close the window and open SMTV again.

A request that stopped can go on: press **Continue** — SMTV picks up from the same step and does not redo what is done.

## 3. Report a problem

Still stuck? Tell us — it helps everyone.

1. **Settings → Computer check → Report a problem** (the **Report…** button; it is also in **Settings → About**), or
   the button under a failed request.
2. SMTV shows what goes into the report: versions, the computer check, settings and logs. **Keys and tokens are cut
   out**, your home folder shows as `~`. Links and file names stay out unless you tick the box.
3. Press **Save and open GitHub**. SMTV saves the archive, and a new issue opens in the browser with the summary filled
   in. Drag the archive into it and press **Submit**.

SMTV sends nothing by itself. Without the window: run `smtv report` in a terminal. You can also
[open an issue](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml) directly.
