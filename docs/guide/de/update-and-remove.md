<!-- languages -->
[English](../update-and-remove.md) · [Русский](../ru/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · **Deutsch**

> 🌐 Diese Seite wurde automatisch übersetzt. Hilf mit, sie zu verbessern: [Weblate](https://hosted.weblate.org/engage/smtv/) · [Pull Request](https://github.com/streammomenttv/smtv/pulls).

# Aktualisieren und entfernen

## Aktualisieren

SMTV sucht einmal am Tag nach einer neuen Version (das kannst du ausschalten). Wenn es eine gibt, zeigt es **Version …
is available** (Version … ist verfügbar): Drücke **Update** (Aktualisieren).

- SMTV schließt sich, aktualisiert sich und öffnet sich von selbst wieder, meist innerhalb einer Minute.
- Läuft gerade ein Auftrag, wartet das Update, bis er fertig ist – oder drücke **Stop the jobs and update** (Aufträge
  anhalten und aktualisieren); **Continue** setzt sie danach beim selben Schritt fort.
- Startet die neue Version nicht, kommt die vorherige von selbst zurück.
- Neue Versionen sind von den Autoren von SMTV signiert; SMTV prüft die Signatur vor der Installation.

Alles zu Updates findest du unter **Settings → Computer check → Updates** (Einstellungen → Computerprüfung → Updates).

SMTV für Windows oder Mac heruntergeladen? **Update** (Aktualisieren) lädt das neue Installationsprogramm herunter,
prüft es und öffnet es: Schließ die Installation dort ab (auf dem Mac zieh das neue SMTV auf Programme und drücke
**Ersetzen** (Replace)). Die Windows-Kopie aus dem ZIP aktualisiert sich nicht selbst: Lade das neue ZIP von
[der Release-Seite](https://github.com/streammomenttv/smtv/releases/latest) herunter.

SMTV auf andere Weise installiert? In Docker ist eine neue Version ein neues Image; siehe [für Fortgeschrittene](../../advanced.md#docker).

## Entfernen

**Settings → Computer check → Remove SMTV from this computer** (SMTV von diesem Computer entfernen; der Knopf
**Remove…**) entfernt das Programm und das SMTV-Symbol. Deine Clips bleiben – setz das Häkchen bei **Also remove clips,
jobs, settings and keys** (Auch Clips, Aufträge, Einstellungen und Schlüssel entfernen), um auch sie zu entfernen.

SMTV für Windows oder Mac heruntergeladen? Entferne das Programm selbst auf dem Weg des Systems (der Knopf oben
entfernt nur die Clips und Einstellungen, wenn du sie anhakst):

- **Windows:** **Einstellungen → Apps → Installierte Apps → SMTV → Deinstallieren** (Settings → Apps → Installed apps →
  SMTV → Uninstall). Die Kopie aus dem ZIP: Lösch ihren Ordner.
- **Mac:** Zieh **SMTV** aus **Programme** (Applications) in den **Papierkorb** (Trash).

Mit einer Zeile im Terminal installiert? Ohne das Fenster, in einem Terminal:

```bash
smtv uninstall
```

Füge `--data` hinzu, um auch die Clips und Einstellungen zu entfernen. Programme, die du selbst installiert hast
(Ollama, LM Studio), bleiben: Entferne sie wie jedes andere Programm.
