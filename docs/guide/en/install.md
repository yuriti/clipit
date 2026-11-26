<!-- languages -->
[Русский](../install.md) · **English** · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 This page was translated automatically from the [Russian original](../install.md). Help improve it: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls).

# Install SMTV

Download one file and open it. Everything SMTV needs is inside. You do not need an administrator password.

| Your computer | Download | Size |
|---|---|---|
| **Windows 10 or 11** (64-bit) | [SMTV for Windows](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip) (ZIP) | about 210 MB |
| **Mac** — Apple silicon (M1 and newer) or Intel, macOS 13+ | [SMTV for Mac](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | about 270 MB |

All versions and their checksums: [the release page](https://github.com/yuriti/clipit/releases/latest).

**Why the system warns you the first time.** SMTV does not have a digital signature yet. The signature for Windows comes
a little later, the one for macOS as soon as possible, and then this warning goes away. SMTV's code is open: anyone can
read what it does.

## Windows

1. Download **SMTV for Windows** — the ZIP `SMTV-windows.zip`.
2. Right-click it → **Extract All** → choose a folder (Documents, for example) → **Extract**.
3. Open the `SMTV` folder and double-click **SMTV.exe**: the SMTV window opens. If Windows shows a blue window
   **«Windows protected your PC»**, press **More info**, then **Run anyway**.
4. So you do not have to look for the folder every time: right-click **SMTV.exe** → **Send to** → **Desktop (create
   shortcut)** (on Windows 11, **Show more options** first).

This copy does not update itself: a new version is a new ZIP, and SMTV tells you when one is out. To remove it, delete
the `SMTV` folder.

**With the installer** — an icon in the Start menu and updates right from the window. While Smart App Control is on
(below), the installer does not start yet.

1. Download [the installer](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows-setup.exe) (the file `SMTV-…-windows-x64-setup.exe`, about 130 MB) and open it.
2. If **«Windows protected your PC»** appears: **More info** → **Run anyway**.
3. The installer asks a couple of questions (language, an icon on the desktop) — press **Next** and **Install**.
4. At the end leave **Launch SMTV** ticked and press **Finish**. Next time start SMTV from the **Start** menu (or the
   desktop icon).

The installer puts SMTV into your own user folder; it appears in **Settings → Apps**, where you can remove it.

### Windows 11: Smart App Control

If **Smart App Control** is on (Windows Security → App & browser control), Windows does not let programs without a
signature start, and there is no button to let them through. SMTV's installer is not signed yet, so it does not start.
You do not need to turn Smart App Control off for SMTV:

1. Take the **ZIP** and open **SMTV.exe** (the steps above): that way SMTV works with Smart App Control on.
2. If that does not open either, install SMTV with [one line in a terminal](#for-experienced-users-one-line-in-a-terminal).

When SMTV is signed, the installer will work there too.

## Mac

1. Download **SMTV for Mac**. It is one file for every Mac, with Apple silicon or Intel: SMTV starts the version made
   for your Mac's processor by itself.
2. Open the downloaded `.dmg`. A window opens with SMTV and the **Applications** folder: drag **SMTV** onto
   **Applications**.
3. Open **Applications** and double-click **SMTV**. macOS says it cannot check SMTV and does not open it. Press
   **Done**.
4. Open **System Settings → Privacy & Security** and scroll down. Next to «SMTV was blocked…» press **Open Anyway**,
   enter your Mac password and press **Open**.
   On macOS 14 there is a shorter way: right-click **SMTV** in Applications → **Open** → **Open**.

Only the first time: after that SMTV opens with a normal click, from Applications or Launchpad. The same steps are in
the file «How to open» inside the `.dmg`.

## The first start

SMTV checks your computer and shows three steps to the first clip. Below them it offers **speech recognition for your
language** — the part that turns the stream's speech into text. It is not inside the download, because each language
needs its own (0.9–2.5 GB). Press **Fix** and watch the progress, or skip it: the first request downloads it by itself.

**What you need:** 5 GB of free space at least, 20 GB for a 6-hour stream; internet. No graphics card is needed.

## For experienced users: one line in a terminal

The same SMTV, installed with [uv](https://astral.sh/uv) — a small official tool for Python programs — into your user
folder. Use it on **Linux**, with **Smart App Control**, or if you prefer a terminal. It updates from the window like the
downloaded app.

**Windows:** press **Start**, type `PowerShell`, open **Windows PowerShell** (the blue window), paste this line (right
click or Ctrl+V) and press **Enter**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

With Smart App Control on, the installer puts SMTV on the signed Python from python.org (it may ask to install it —
agree) and starts SMTV through it. If a terminal says it cannot run `smtv`, use the **SMTV** icon instead.

**Mac or Linux:** open **Terminal** (on a Mac: Cmd+Space, type `Terminal`, Enter), paste this line and press **Enter**:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

Wait until it says it is done (2–10 minutes). SMTV opens by itself; the **SMTV** icon is in the Start menu on Windows,
in Applications on a Mac, in the applications menu on Linux. On this way SMTV offers to install **ffmpeg** (the video
tool) with **Fix** the first time; the download above has it inside.

Both installers are short and open: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## If the system warns you

- **Windows: «Windows protected your PC»** (SmartScreen). Press **More info**, then **Run anyway**.
- **Windows 11: Smart App Control blocks SMTV.** Until SMTV is signed, take the ZIP and open **SMTV.exe**; if that does
  not help, install SMTV with [one line in a terminal](#for-experienced-users-one-line-in-a-terminal).
- **Windows: the firewall asks** whether SMTV may use the network. Allow it for **private** networks: SMTV needs it to
  open on your phone. Saying no is fine if you do not need the phone.
- **Mac: «SMTV cannot be opened»**, «Apple could not verify…» or «developer cannot be verified». Open **System
  Settings → Privacy & Security**, scroll down and press **Open Anyway** next to SMTV.
- **Mac: «SMTV would like to accept incoming connections»** — allow it if you want to use SMTV on your phone.
- **Antivirus** complains? SMTV is new and not signed yet, so some antiviruses are careful with it. Its code is open, and
  the checksums of every file are on [the release page](https://github.com/yuriti/clipit/releases/latest)
  (`SHA256SUMS.txt`).

Next: [your first clip](first-clip.md).
