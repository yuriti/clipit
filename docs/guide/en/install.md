<!-- languages -->
[Русский](../install.md) · **English** · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 This page was translated automatically from the [Russian original](../install.md). Help improve it: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls).

# Install Clip It!

Download one file and open it. Everything Clip It! needs is inside. You do not need an administrator password.

| Your computer | Download | Size |
|---|---|---|
| **Windows 10 or 11** (64-bit) | [Clip It! for Windows](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip) (ZIP) | about 100 MB |
| **Mac** — Apple silicon (M1 and newer) or Intel, macOS 13+ | [Clip It! for Mac](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | about 270 MB |

All versions and their checksums: [the release page](https://github.com/yuriti/clipit/releases/latest).

**Why the system warns you the first time.** Clip It! does not have a digital signature yet. The signature for Windows comes
a little later, the one for macOS as soon as possible, and then this warning goes away. Clip It!'s code is open: anyone can
read what it does.

It was called SMTV before: if you have it, the new version takes its place, and your settings and clips stay.

## Windows

There is no installer: Clip It! for Windows is a folder you unzip and start.

1. Download **Clip It! for Windows** — the ZIP `SMTV-windows.zip`.
2. Right-click it → **Extract All** → choose a folder (Documents, for example) → **Extract**.
3. Open the `ClipIt` folder. It holds **ClipIt.exe**, a file «Как запустить Clip It!» (how to start Clip It!, in Russian and
   English), an `app` folder with the program's parts (leave it alone) and a `Clips` folder. Double-click **ClipIt.exe**
   (it has Python's icon, and that is right): the Clip It! window opens. If Windows shows a blue window **«Windows
   protected your PC»**, press **More info**, then **Run anyway**.

**Everything is kept in this folder**: settings, AI keys, speech recognition models (about 2.4 GB). Finished clips are in
the `Clips` folder. Clip It! makes no shortcuts and no files anywhere else. So:

- keep the whole folder together in one place, for example in Documents; for a shortcut, right-click **ClipIt.exe** →
  **Send to** → **Desktop (create shortcut)** (on Windows 11, **Show more options** first);
- do not give the folder to other people: your keys are in it;
- do not put it in a folder OneDrive syncs, or in Program Files (nothing can be written there, and Clip It! says so).

**Updates** come from the window: Clip It! downloads the new version and replaces the program in this same folder; your
settings and clips are left as they are. **To remove it**, delete the `ClipIt` folder, or in the window: **Settings →
System → Remove Clip It! from this computer**.

If you have the earlier version (SMTV, with its installer), Clip It! offers once, at its first start, to copy its
settings and keys into the new folder. Remove the old version the usual way: **Settings → Apps → SMTV → Uninstall**.

### Windows 11: Smart App Control

If **Smart App Control** is on (Windows Security → App & browser control), Windows does not let programs without a
signature start, and there is no button to let them through. You do not need to turn it off for Clip It!:

1. Take the **ZIP** and open **ClipIt.exe** (the steps above): that way Clip It! works with Smart App Control on.
2. If that does not open either, install Clip It! with [one line in a terminal](#for-experienced-users-one-line-in-a-terminal).

## Mac

1. Download **Clip It! for Mac**. It is one file for every Mac, with Apple silicon or Intel: Clip It! starts the version made
   for your Mac's processor by itself.
2. Open the downloaded `.dmg`. A window opens with Clip It! and the **Applications** folder: drag **Clip It!** onto
   **Applications**.
3. Open **Applications** and double-click **Clip It!**. macOS says it cannot check Clip It! and does not open it. Press
   **Done**.
4. Open **System Settings → Privacy & Security** and scroll down. Next to «Clip It! was blocked…» press **Open Anyway**,
   enter your Mac password and press **Open**.
   On macOS 14 there is a shorter way: right-click **Clip It!** in Applications → **Open** → **Open**.

Only the first time: after that Clip It! opens with a normal click, from Applications or Launchpad. The same steps are in
the file «How to open» inside the `.dmg`.

## The first start

Clip It! checks your computer and shows three steps to the first clip. Below them it offers **speech recognition for your
language** — the part that turns the stream's speech into text. It is not inside the download, because each language
needs its own (0.9–2.5 GB). Press **Fix** and watch the progress, or skip it: the first request downloads it by itself.

**What you need:** 5 GB of free space at least, 20 GB for a 6-hour stream; internet. No graphics card is needed.

## For experienced users: one line in a terminal

The same Clip It!, installed with [uv](https://astral.sh/uv) — a small official tool for Python programs — into your user
folder. Use it on **Linux**, with **Smart App Control**, or if you prefer a terminal. It updates from the window like the
downloaded app.

**Windows:** press **Start**, type `PowerShell`, open **Windows PowerShell** (the blue window), paste this line (right
click or Ctrl+V) and press **Enter**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

With Smart App Control on, the installer puts Clip It! on the signed Python from python.org (it may ask to install it —
agree) and starts Clip It! through it. If a terminal says it cannot run `smtv`, use the **Clip It!** icon instead.

**Mac or Linux:** open **Terminal** (on a Mac: Cmd+Space, type `Terminal`, Enter), paste this line and press **Enter**:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

Wait until it says it is done (2–10 minutes). Clip It! opens by itself; the **Clip It!** icon is in the Start menu on Windows,
in Applications on a Mac, in the applications menu on Linux. On this way Clip It! offers to install **ffmpeg** (the video
tool) with **Fix** the first time; the download above has it inside.

Both installers are short and open: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## If the system warns you

- **Windows: «Windows protected your PC»** (SmartScreen). Press **More info**, then **Run anyway**.
- **Windows 11: Smart App Control blocks Clip It!** Until Clip It! is signed, take the ZIP and open **ClipIt.exe**; if that does
  not help, install Clip It! with [one line in a terminal](#for-experienced-users-one-line-in-a-terminal).
- **Windows: the firewall asks** whether Clip It! may use the network. Allow it for **private** networks: Clip It! needs it to
  open on your phone. Saying no is fine if you do not need the phone.
- **Mac: «Clip It! cannot be opened»**, «Apple could not verify…» or «developer cannot be verified». Open **System
  Settings → Privacy & Security**, scroll down and press **Open Anyway** next to Clip It!
- **Mac: «Clip It! would like to accept incoming connections»** — allow it if you want to use Clip It! on your phone.
- **Antivirus** complains? Clip It! is new and not signed yet, so some antiviruses are careful with it. Its code is open, and
  the checksums of every file are on [the release page](https://github.com/yuriti/clipit/releases/latest)
  (`SHA256SUMS.txt`).

Next: [your first clip](first-clip.md).
