<!-- The source is the Russian README.md; translations: README.<language>.md, the same structure. A change to README.md
     changes README.en.md in the same PR; the other languages follow (each says it was translated automatically from
     the Russian original and links it and Weblate). Pictures: docs/images/. -->
<div align="center">

# SMTV

**Mach aus einem langen Stream kurze Clips und eine Zusammenfassung. Kostenlos, auf deinem eigenen Computer.**

<!-- languages -->
[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md) · [Oʻzbekcha](README.uz.md) · [Azərbaycanca](README.az.md) · [Кыргызча](README.ky.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [हिन्दी](README.hi.md) · [বাংলা](README.bn.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · **Deutsch**

> 🌐 Diese Seite wurde automatisch übersetzt. Hilf mit, sie zu verbessern: [Weblate](https://hosted.weblate.org/engage/smtv/) · [Pull Request](https://github.com/yuriti/clipit/pulls) · [Original: Русский](README.md).

[![Neueste Version](https://img.shields.io/github/v/release/yuriti/clipit?label=release)](https://github.com/yuriti/clipit/releases/latest)
[![Downloads](https://img.shields.io/pepy/dt/smtv?label=downloads)](https://pepy.tech/projects/smtv)
[![Sterne](https://img.shields.io/github/stars/yuriti/clipit?style=flat)](https://github.com/yuriti/clipit/stargazers)
[![Lizenz: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/smtv)](https://pypi.org/project/smtv/)
[![Auf Weblate übersetzen](https://hosted.weblate.org/widget/smtv/svg-badge.svg)](https://hosted.weblate.org/engage/smtv/)

<img src="docs/images/demo.gif" alt="SMTV: Eine Stream-Aufnahme kommt rein, SMTV findet die besten Momente und macht nacheinander vertikale Clips" width="820">

[**SMTV herunterladen**](#herunterladen) · [Schritt-für-Schritt-Anleitungen](docs/guide/de/README.md) · [Im Vergleich](#smtv-im-vergleich) · [Fragen](#fragen)

</div>

---

Du hast sechs Stunden gestreamt. Irgendwo darin stecken die zehn Momente, die sich zu posten lohnen – aber um sie zu
finden, müsstest du alles noch einmal anschauen. **SMTV schaut es für dich.** Füge einen Link zu einer Twitch- oder
YouTube-Aufnahme ein oder wähle eine Videodatei, und SMTV hört sich den ganzen Stream an, wählt die besten Momente aus
und gibt dir **fertige vertikale Clips** für TikTok, Shorts und Reels – mit Untertiteln und der Webcam oben – sowie eine
**Zusammenfassung von 20–30 Minuten** des ganzen Streams für YouTube.

## Was es macht

| | |
|---|---|
| 🎬 **Clips, die bereit zum Posten sind** | Vertikal 9:16, mit großen Untertiteln, einer kurzen Titelkarte am Anfang und der Webcam des Streamers über dem Spiel. |
| ⏱️ **Lange Streams sind kein Problem** | Eine Aufnahme von 6–12 Stunden rein, bis zu 30 Clips raus. Die Clips erscheinen nacheinander: Du kannst posten, bevor der Rest fertig ist. |
| 📺 **Eine Zusammenfassung des ganzen Streams** | Ein Video von 20–30 Minuten für YouTube: der Stream selbst, gekürzt auf die sehenswerten Teile. |
| 🗣️ **Viele Sprachen** | Russisch, 25 europäische Sprachen und Dutzende weitere. SMTV wandelt Sprache direkt auf deinem Computer in Text um. |
| 🔒 **Deine Dateien bleiben bei dir** | Clips werden auf deinem Computer erstellt und gespeichert. Nichts wird auf eine Website hochgeladen. |
| 💸 **Kostenlos und offen** | MIT-Lizenz: nutzen, weitergeben, für Kunden einsetzen. Kein Wasserzeichen, kein Minutenlimit. |

## So sieht es aus

**Link einfügen oder Datei wählen – und den Schritten zusehen.** Jeder Schritt ist auf dem Bildschirm: Sprache zu
Text, Momente finden, sie bewerten, jeden Clip schneiden.

<img src="docs/images/new-request.gif" alt="Ein neuer Auftrag: Eine Videodatei wird gewählt, SMTV startet und zeigt jeden Schritt" width="820">

**Die Clips erscheinen nacheinander.** Schau sie direkt in SMTV an, lade sie herunter, poste sie.

<img src="docs/images/clips.png" alt="Fertige Clips eines Streams in einem Raster" width="820">

**Zu jedem Clip gibt es den Text.** Lies, was gesagt wurde und warum SMTV den Moment ausgewählt hat.

<img src="docs/images/viewer.png" alt="Ein Clip läuft neben seinem Transkript" width="820">

**Und eine Zusammenfassung des ganzen Streams** für YouTube, erstellt nach den Clips.

<img src="docs/images/recap.png" alt="Die Zusammenfassung des Streams in SMTV" width="820">

**Hell oder dunkel** – wie auf deinem Computer.

<img src="docs/images/dark.png" alt="SMTV im dunklen Design" width="820">

<sub>Der Stream auf diesen Bildern ist für die Demo ausgedacht: ein kleines Spiel, ein Cartoon-Maskottchen statt einer
Webcam und eine Computerstimme. Keine echte Person ist zu sehen.</sub>

## Kostenlos und Open Source

- **SMTV ist kostenlos.** Das ganze Programm ist Open Source unter der [MIT-Lizenz](LICENSE): Nutze es für dich, für
  deinen Kanal oder für Kunden, ändere es und gib es weiter.
- **Kein Wasserzeichen, keine Minutenlimits, kein Abo bei SMTV.**
- **Du zahlst nur für die KI, und nur wenn du willst.** SMTV braucht eine KI, die den Text des Streams liest und die
  Momente auswählt. Das kann eine kostenlose KI auf deinem eigenen Computer sein oder ein Dienst deiner Wahl – siehe
  unten.
- **Deine Daten bleiben bei dir.** Clips werden auf deinem Computer erstellt und gespeichert. Nur der Text des Streams
  geht an die KI, die du gewählt hast. Mit einer kostenlosen KI auf deinem Computer verlässt gar nichts den Rechner.

## Wähle deine KI: drei Wege

SMTV wandelt die Sprache selbst auf deinem Computer in Text um. Um die besten Momente auszuwählen, fragt es eine KI.
Wähle einen Weg – einer reicht, und du kannst ihn jederzeit in **Settings → AI** (Einstellungen → KI) ändern.

| | Wie | Kosten | Gut für |
|---|---|---|---|
| ⭐ **Über das Konto** | Melde dich bei einem StreamMoment-Konto an (Google, Twitch oder Telegram) und lade das Guthaben auf. Das ist alles: keine Schlüssel, keine Einrichtung. | Bezahlung nach Verbrauch vom Guthaben | Alle: der einfachste Weg. Wird auch gebraucht, um **Links** zu Aufnahmen einzufügen. [Anleitung](docs/guide/de/account.md) |
| 🔑 **Dein eigener Schlüssel** | Du nutzt schon OpenAI, Claude, Gemini oder OpenRouter? Füge deinen Schlüssel ein, und SMTV nutzt ihn direkt. | Du bezahlst diesen Dienst direkt; manche haben einen kostenlosen Tarif | Alle, die schon einen KI-Dienst nutzen. [Wo man einen Schlüssel bekommt](docs/guide/de/get-a-key.md) |
| 💻 **Kostenlos, auf deinem Computer** | Installiere Ollama oder LM Studio und ein Qwen-Modell; SMTV findet es von selbst. | Kostenlos | Ein Computer mit starker Grafikkarte. Die Clips werden schwächer. [Anleitung](docs/guide/de/free-ai-on-your-computer.md) |

## Herunterladen

| Dein Computer | Download | Größe |
|---|---|---|
| **Windows 10 oder 11** (64-Bit) | [**SMTV für Windows**](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows-setup.exe) (Installationsprogramm) | etwa 130 MB |
| **Mac** — Apple Silicon (M1 und neuer) oder Intel, macOS 13+ | [**SMTV für Mac**](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | etwa 270 MB |

Eine Datei für jeden Mac: SMTV startet von selbst die Version, die für den Prozessor deines Macs gebaut ist. Windows ganz ohne Installation:
[das ZIP](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip) – entpacke es und öffne
**Start SMTV**.

Alles, was SMTV braucht, ist schon drin: das Programm, Python und ffmpeg mit Untertiteln. Die Spracherkennung wird beim
ersten Start heruntergeladen, nur für deine Sprache (0,9–2,5 GB, einmalig): SMTV bietet sie mit einem Knopf an, **Fix**
(Beheben).

**Beim ersten Mal warnt dich das System.** SMTV hat noch keine digitale Signatur: Die für Windows kommt etwas später,
die für macOS so bald wie möglich, und dann verschwindet diese Warnung. Bis dahin:

- **Windows** («Der Computer wurde durch Windows geschützt»): **Weitere Informationen** (More info) → **Trotzdem
  ausführen** (Run anyway).
- **Mac**: Öffne SMTV einmal, dann **Systemeinstellungen → Datenschutz & Sicherheit** (System Settings → Privacy &
  Security) → **Dennoch öffnen** (Open Anyway).
- **Windows 11 mit Smart App Control** blockiert Programme ohne Signatur komplett, und es gibt keinen Knopf, um sie
  durchzulassen. Nimm die Installation in einer Zeile weiter unten: Sie funktioniert bei eingeschaltetem Smart App
  Control. Sobald SMTV signiert ist, funktioniert dort auch der Download.

[Jeder Schritt mit Bildern](docs/guide/de/install.md).

### Für Erfahrene: eine Zeile im Terminal

Dasselbe SMTV, mit [uv](https://astral.sh/uv) in deinen Benutzerordner installiert. Es funktioniert auch unter
**Linux** und mit **Smart App Control** und aktualisiert sich genauso über das Fenster.

**Windows** – drücke Start, tippe **PowerShell**, öffne es und füge ein:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

**Mac oder Linux** – öffne das **Terminal** und füge ein:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

Drücke Enter und warte ein paar Minuten. Ein Administratorpasswort ist nicht nötig. Ein **SMTV**-Symbol erscheint –
unter Windows auf dem Desktop und im Startmenü, auf dem Mac in „Programme“, unter Linux im Anwendungsmenü.

## Dein erster Clip in drei Schritten

1. **Wähle eine KI** – beim ersten Start zeigt das Fenster die drei Wege ([welche?](docs/guide/de/connect-ai.md)).
2. **Füge einen Link** zu einer Twitch- oder YouTube-Aufnahme ein oder wähle eine Videodatei von deinem Computer.
3. **Warte.** Die Clips erscheinen nacheinander: anschauen, herunterladen, posten.

Beim ersten Mal prüft SMTV deinen Computer und bietet an, Fehlendes mit einem Knopf zu beheben: **Fix** (Beheben).
[Der erste Clip, Schritt für Schritt](docs/guide/de/first-clip.md).

## Schritt-für-Schritt-Anleitungen

Für alle, für die das alles neu ist – jeder Schritt, mit Bildern:

| | |
|---|---|
| [Installieren unter Windows, Mac oder Linux](docs/guide/de/install.md) | und was zu tun ist, wenn das System warnt |
| [Dein erster Clip](docs/guide/de/first-clip.md) | von einem Link oder einer Datei zum fertigen Clip |
| [Welche KI wählen](docs/guide/de/connect-ai.md) | die drei Wege im Vergleich |
| [Eine kostenlose KI auf deinem Computer](docs/guide/de/free-ai-on-your-computer.md) | Ollama oder LM Studio mit Qwen: welches Modell zu deiner Grafikkarte passt |
| [Wo man einen Schlüssel bekommt](docs/guide/de/get-a-key.md) | welche Dienste einen kostenlosen oder günstigen Tarif haben, Schritt für Schritt |
| [Das StreamMoment-Konto](docs/guide/de/account.md) | Anmeldung, Guthaben |
| [SMTV auf dem Handy](docs/guide/de/phone.md) | QR-Code scannen und die Clips auf dem Handy ansehen |
| [Sprache und Sprachen](docs/guide/de/speech-and-languages.md) | welche Sprachen SMTV versteht |
| [Aktualisieren und entfernen](docs/guide/de/update-and-remove.md) | |
| [Etwas ist schiefgelaufen](docs/guide/de/troubleshooting.md) | Computerprüfung, **Fix**, **Report a problem** |

## SMTV im Vergleich

Die meistgenutzten Open-Source-Clipper, nach dem eigenen Code und der Dokumentation jedes Projekts, **Stand November
2026**. Das sind gute Projekte, jedes für seine eigene Aufgabe gemacht; diese Tabelle zeigt nur, worin sich SMTV
unterscheidet. Hat sich etwas geändert? [Sag es uns](https://github.com/yuriti/clipit/issues/new?template=bug.yml),
und wir korrigieren die Tabelle.

| | **SMTV** | [openshorts](https://github.com/mutonby/openshorts) | [SupoClip](https://github.com/FujiwaraChoki/supoclip) | [PeakCut](https://github.com/haziqahmedqasmi/PeakCut) | [FunClip](https://github.com/modelscope/FunClip) |
|---|---|---|---|---|---|
| Lizenz | **MIT** | MIT (der Ordner `cloud/` hat eine eigene Lizenz) | Quelltext-Lizenz, nicht kommerziell | MIT | MIT |
| Ein ganzer Stream von 6–12 Stunden | **Ja** | Standardmäßig 60 Minuten pro Auftrag | Standardmäßig 90 Minuten | Kein Längenlimit angegeben | Nicht für Streams gemacht |
| Eine lange Zusammenfassung des ganzen Streams | **Ja, 20–30 Minuten** | Nein | Nein (sein «recap» ist ein einzelner kurzer Clip) | Nein | Nein |
| Russische Sprache | **GigaAM-v3, für Russisch gemacht** | Whisper oder Parakeet v3 | AssemblyAI oder Whisper | Nein (Parakeet v2, nur Englisch) | Nein (Chinesisch und Englisch) |
| Webcam des Streamers im vertikalen Bild | **Ja** | Nein | Gaming-Modus, standardmäßig aus | Ja | Keine vertikalen Clips |
| Sprache zu Text standardmäßig | **Auf deinem Computer, kostenlos** | Auf deinem Computer | AssemblyAI, ein kostenpflichtiger Dienst | Auf deinem Computer | Auf deinem Computer |
| Wie man es startet | **Eigenes Fenster und Symbol: Download für Windows und Mac oder eine Zeile** | Webseite in Docker | Webseite in Docker | Webseite | Webseite |

## Fragen

<details>
<summary><b>Ist es wirklich kostenlos?</b></summary>

Ja. SMTV selbst kostet nichts und hat keine Limits. Die einzigen möglichen Kosten sind die der KI, die die Momente
auswählt: kostenlos auf deinem eigenen Computer oder bezahlt an den Dienst deiner Wahl (über das StreamMoment-Konto
oder deinen eigenen Schlüssel).
</details>

<details>
<summary><b>Brauche ich einen leistungsstarken Computer?</b></summary>

Eine Grafikkarte ist nicht nötig: SMTV läuft auf einem normalen Computer, nur langsamer. Eine NVIDIA-Karte macht die
Umwandlung von Sprache zu Text schneller. Eine kostenlose KI auf deinem eigenen Computer ist die Ausnahme – sie braucht
eine starke Grafikkarte ([welche](docs/guide/de/free-ai-on-your-computer.md)). Freier Speicherplatz: mindestens 5 GB,
20 GB für einen 6-Stunden-Stream.
</details>

<details>
<summary><b>Wie lange dauert es?</b></summary>

Gemessen auf einem Mac mit Apple Silicon, ohne Grafikkarte: Bei einer Twitch-Aufnahme von 2,35 Stunden dauerte es etwa
6 Minuten, die Momente zu finden, danach etwa 1 Minute pro Clip; eine Zusammenfassung von 10,7 Minuten dauerte
6,5 Minuten. Bevor ein Auftrag startet, zeigt SMTV, wie lange er dauern sollte.
</details>

<details>
<summary><b>Auf welchen Systemen läuft es?</b></summary>

Windows 10 (Version 1809) oder neuer, 64-Bit; macOS 13 oder neuer auf Apple Silicon und Intel (auf Apple Silicon läuft SMTV ab macOS 14 nativ; unter macOS 13 startet es seine Intel-Version über Rosetta, langsamer);
Linux (Installation in einer Zeile). Geprüft unter Windows 11 und auf Macs mit Apple Silicon; Intel-Macs (nur unter
Rosetta) und Linux-Desktops sind noch nicht getestet.
</details>

<details>
<summary><b>Welche Sprachen versteht es?</b></summary>

Russisch, 25 europäische Sprachen und Dutzende weitere. SMTV erkennt die Sprache des Streams von selbst.
[Details](docs/guide/de/speech-and-languages.md).
</details>

<details>
<summary><b>Darf ich die Clips für meine Kunden verwenden?</b></summary>

Ja. Die MIT-Lizenz erlaubt jede Nutzung, auch kommerziell: Clipping für Streamer, Agenturen, deine eigenen Kanäle.
Achte die Rechte des Streamers, dessen Stream du schneidest.
</details>

<details>
<summary><b>Wo landen meine Clips? Wird etwas hochgeladen?</b></summary>

Die Clips bleiben auf deinem Computer. Eine eigene Videodatei verlässt ihn nie. Ein Link wird über das
StreamMoment-Konto abgerufen: Dessen Server reicht die Aufnahme in Stücken an SMTV weiter und speichert nichts. Der Text
des Streams geht nur an die KI, die du gewählt hast. Schlüssel für KI-Dienste bleiben auf deinem Computer und tauchen
nie in Logs oder Problemberichten auf.
</details>

<details>
<summary><b>Postet es selbst auf TikTok oder YouTube?</b></summary>

Noch nicht: Du lädst die Clips herunter und postest sie selbst. Settings → About → «Coming» (Einstellungen → Über →
Demnächst) zeigt, was geplant ist.
</details>

<details>
<summary><b>Etwas funktioniert nicht.</b></summary>

Settings → **Computer check** → **Fix** (Einstellungen → Computerprüfung → Beheben) löst die meisten Probleme. Kommst
du trotzdem nicht weiter? Settings → Computer check → **Report…**: SMTV bereitet einen Bericht ohne deine Schlüssel vor
und öffnet eine Seite auf GitHub; nichts wird von selbst gesendet.
[Was du versuchen kannst](docs/guide/de/troubleshooting.md).
</details>

## Hilf, SMTV zu übersetzen

Das Fenster von SMTV spricht die Sprache deines Computers. Übersetzungen machen Menschen auf
[Weblate](https://hosted.weblate.org/engage/smtv/) – ohne Programmieren: Seite öffnen, Sprache wählen, ein paar Zeilen
übersetzen. Die Übersetzungen dieser Seite wurden automatisch erstellt; wenn du einen Fehler siehst, korrigiere ihn in
einem Pull Request. [Wie Übersetzungen funktionieren](docs/translations.md).

[![Übersetzungsstand](https://hosted.weblate.org/widget/smtv/multi-auto.svg)](https://hosted.weblate.org/engage/smtv/)

## StreamMoment

SMTV wird vom Team von [StreamMoment](https://streammoment.tv) gemacht. Das StreamMoment-Konto ist der einfachste Weg,
SMTV eine KI zu geben und Links zu Aufnahmen einzufügen; SMTV funktioniert auch ohne es.

- [Problem melden](https://github.com/yuriti/clipit/issues/new?template=bug.yml) · [Idee vorschlagen](https://github.com/yuriti/clipit/issues/new?template=feature.yml)
- [Für Fortgeschrittene](docs/advanced.md): Docker, alle KI-Dienste, Sprachmodelle, Schlüssel, Befehle
- [Änderungen](CHANGELOG.md) · [Mitmachen](CONTRIBUTING.md) · [Sicherheit](SECURITY.md)
- Gefällt dir SMTV? [Unterstütze es auf Boosty](https://boosty.to/smtv) und gib dem Repository einen ⭐ – so finden es
  auch andere.

Lizenz: [MIT](LICENSE).
