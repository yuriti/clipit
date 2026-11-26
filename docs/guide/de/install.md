<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · **Deutsch**

> 🌐 Diese Seite wurde automatisch übersetzt. Hilf mit, sie zu verbessern: [Weblate](https://hosted.weblate.org/engage/smtv/) · [Pull Request](https://github.com/yuriti/clipit/pulls) · [Original: Русский](../install.md).

# SMTV installieren

Lade eine Datei herunter, öffne sie, und ein **SMTV**-Symbol erscheint. Alles, was SMTV braucht, ist schon drin. Du
brauchst kein Administratorpasswort.

| Dein Computer | Download | Größe |
|---|---|---|
| **Windows 10 oder 11** (64-Bit) | [SMTV für Windows](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows-setup.exe) | etwa 130 MB |
| **Mac** — Apple Silicon (M1 und neuer) oder Intel, macOS 13+ | [SMTV für Mac](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | etwa 270 MB |

Alle Versionen und ihre Prüfsummen: [die Release-Seite](https://github.com/yuriti/clipit/releases/latest).

**Warum das System beim ersten Mal warnt.** SMTV hat noch keine digitale Signatur. Die Signatur für Windows kommt etwas
später, die für macOS so bald wie möglich, und dann verschwindet diese Warnung. Der Code von SMTV ist offen: Jeder kann
nachlesen, was es tut.

## Windows

1. Lade **SMTV für Windows** herunter (die Datei `SMTV-…-windows-x64-setup.exe`) und öffne sie.
2. Windows zeigt ein blaues Fenster **«Der Computer wurde durch Windows geschützt»** («Windows protected your PC»).
   Drücke **Weitere Informationen** (More info), dann **Trotzdem ausführen** (Run anyway).
3. Das Installationsprogramm stellt ein paar Fragen (Sprache, ein Symbol auf dem Desktop) – drücke **Weiter** (Next)
   und **Installieren** (Install).
4. Lass am Ende **SMTV starten** (Launch SMTV) angehakt und drücke **Fertigstellen** (Finish). Beim nächsten Mal
   startest du SMTV über das **Startmenü** (oder das Symbol auf dem Desktop).

Das Installationsprogramm legt SMTV in deinen eigenen Benutzerordner; es erscheint unter **Einstellungen → Apps**
(Settings → Apps), wo du es entfernen kannst.

**Ohne Installation:** Lade [das ZIP](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip)
herunter, entpacke es irgendwohin (zum Beispiel in Dokumente) und öffne **SMTV.exe** im Ordner `SMTV`. Diese Kopie
aktualisiert sich nicht selbst: Eine neue Version ist ein neues ZIP.

### Windows 11: Smart App Control

Wenn **Smart App Control** (Intelligente App-Steuerung) eingeschaltet ist (Windows-Sicherheit → App- & Browsersteuerung),
blockiert Windows Programme ohne Signatur komplett, und es gibt keinen Knopf, um sie durchzulassen. Du musst Smart App
Control für SMTV nicht ausschalten. Installiere SMTV stattdessen mit einer Zeile – das funktioniert bei eingeschaltetem
Smart App Control: [eine Zeile im Terminal](#für-erfahrene-eine-zeile-im-terminal). Sobald SMTV signiert ist,
funktioniert dort auch der Download.

## Mac

1. Lade **SMTV für Mac** herunter. Es ist eine Datei für jeden Mac, mit Apple Silicon oder Intel: SMTV startet von selbst die Version, die für den Prozessor deines Macs gebaut ist.
2. Öffne die heruntergeladene `.dmg`. Ein Fenster mit SMTV und dem Ordner **Programme** (Applications) öffnet sich:
   Zieh **SMTV** auf **Programme**.
3. Öffne **Programme** und doppelklicke auf **SMTV**. macOS meldet, dass es SMTV nicht überprüfen kann, und öffnet es
   nicht. Drücke **Fertig** (Done).
4. Öffne **Systemeinstellungen → Datenschutz & Sicherheit** (System Settings → Privacy & Security) und scrolle nach
   unten. Drücke neben «SMTV wurde blockiert …» auf **Dennoch öffnen** (Open Anyway), gib dein Mac-Passwort ein und
   drücke **Öffnen** (Open).
   Unter macOS 14 geht es kürzer: Rechtsklick auf **SMTV** in Programme → **Öffnen** → **Öffnen**.

Nur beim ersten Mal: Danach öffnet sich SMTV mit einem normalen Klick, aus Programme oder dem Launchpad. Dieselben
Schritte stehen in der Datei «How to open» in der `.dmg`.

## Der erste Start

SMTV prüft deinen Computer und zeigt drei Schritte bis zum ersten Clip. Darunter bietet es die **Spracherkennung für
deine Sprache** an – den Teil, der das Gesprochene im Stream in Text verwandelt. Sie ist nicht im Download enthalten,
weil jede Sprache ihre eigene braucht (0,9–2,5 GB). Drücke **Fix** (Beheben) und schau dem Fortschritt zu, oder
überspring es: Der erste Auftrag lädt sie von selbst herunter.

**Was du brauchst:** mindestens 5 GB freien Speicherplatz, 20 GB für einen 6-Stunden-Stream; Internet. Eine
Grafikkarte ist nicht nötig.

## Für Erfahrene: eine Zeile im Terminal

Dasselbe SMTV, mit [uv](https://astral.sh/uv) – einem kleinen offiziellen Werkzeug für Python-Programme – in deinen
Benutzerordner installiert. Nimm es unter **Linux**, mit **Smart App Control** oder wenn du lieber ein Terminal
benutzt. Es aktualisiert sich über das Fenster wie die heruntergeladene App.

**Windows:** Drücke **Start**, tippe `PowerShell`, öffne **Windows PowerShell** (das blaue Fenster), füge diese Zeile
ein (Rechtsklick oder Strg+V) und drücke **Enter**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

Bei eingeschaltetem Smart App Control installiert das Installationsprogramm SMTV auf dem signierten Python von
python.org (es fragt eventuell, ob es das installieren darf – stimm zu) und startet SMTV darüber. Wenn ein Terminal
sagt, dass es `smtv` nicht ausführen kann, nimm stattdessen das **SMTV**-Symbol.

**Mac oder Linux:** Öffne das **Terminal** (auf dem Mac: Cmd+Leertaste, tippe `Terminal`, Enter), füge diese Zeile ein
und drücke **Enter**:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

Warte, bis es meldet, dass es fertig ist (2–10 Minuten). SMTV öffnet sich von selbst; das **SMTV**-Symbol ist unter
Windows im Startmenü, auf dem Mac in „Programme“, unter Linux im Anwendungsmenü. Auf diesem Weg bietet SMTV beim
ersten Mal an, **ffmpeg** (das Videowerkzeug) mit **Fix** zu installieren; im Download oben ist es schon drin.

Beide Installationsprogramme sind kurz und offen: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## Wenn das System warnt

- **Windows: «Der Computer wurde durch Windows geschützt»** («Windows protected your PC», SmartScreen). Drücke
  **Weitere Informationen** (More info), dann **Trotzdem ausführen** (Run anyway).
- **Windows 11: Smart App Control blockiert SMTV.** Nimm [eine Zeile im Terminal](#für-erfahrene-eine-zeile-im-terminal),
  bis SMTV signiert ist.
- **Windows: Die Firewall fragt**, ob SMTV das Netzwerk nutzen darf. Erlaube es für **private** Netzwerke: SMTV braucht
  das, um sich auf deinem Handy zu öffnen. Ablehnen ist in Ordnung, wenn du das Handy nicht brauchst.
- **Mac: «SMTV kann nicht geöffnet werden»**, «Apple konnte nicht überprüfen …» oder «Entwickler kann nicht überprüft
  werden». Öffne **Systemeinstellungen → Datenschutz & Sicherheit** (System Settings → Privacy & Security), scrolle
  nach unten und drücke **Dennoch öffnen** (Open Anyway) neben SMTV.
- **Mac: «SMTV möchte eingehende Netzwerkverbindungen akzeptieren»** – erlaube es, wenn du SMTV auf dem Handy nutzen
  willst.
- **Das Antivirenprogramm** beschwert sich? SMTV ist neu und noch nicht signiert, deshalb sind manche Antivirenprogramme
  vorsichtig damit. Sein Code ist offen, und die Prüfsummen jeder Datei stehen auf [der Release-Seite](https://github.com/yuriti/clipit/releases/latest)
  (`SHA256SUMS.txt`).

Weiter: [dein erster Clip](first-clip.md).
