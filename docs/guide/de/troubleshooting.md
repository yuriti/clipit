<!-- languages -->
[Русский](../troubleshooting.md) · [English](../en/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · [한국어](../ko/troubleshooting.md) · [Tiếng Việt](../vi/troubleshooting.md) · [Bahasa Indonesia](../id/troubleshooting.md) · [हिन्दी](../hi/troubleshooting.md) · [বাংলা](../bn/troubleshooting.md) · [Español](../es/troubleshooting.md) · [Português](../pt-BR/troubleshooting.md) · **Deutsch**

> 🌐 Diese Seite wurde automatisch übersetzt. Hilf mit, sie zu verbessern: [Weblate](https://hosted.weblate.org/engage/smtv/) · [Pull Request](https://github.com/streammomenttv/smtv/pulls) · [Original: Русский](../troubleshooting.md).

# Etwas ist schiefgelaufen

## 1. Computer check → Fix

**Settings → Computer check** (Einstellungen → Computerprüfung) schaut sich alles an, was SMTV braucht, und sagt Zeile
für Zeile, was in Ordnung ist und was nicht. Neben einem Problem steht ein Knopf **Fix** (Beheben): SMTV installiert
oder repariert, was es selbst kann, und zeigt, was es tut.

<img src="../../images/check.png" alt="Settings → Computer check: jede Zeile mit ihrem Zustand und einem Fix-Knopf" width="820">

| Die Zeile sagt | Was tun |
|---|---|
| **Video (ffmpeg)** fehlt | Drücke **Fix**: SMTV installiert ffmpeg, das Videowerkzeug, das es nutzt. |
| **Captions** (Untertitel) funktionieren nicht | Drücke **Fix**: SMTV installiert ein ffmpeg, das Untertitel zeichnen kann. |
| **AI** (KI): nichts verbunden | Wähle eine in **Settings → AI** – [welche](connect-ai.md). |
| **Connection to StreamMoment** (Verbindung zu StreamMoment) schlägt fehl | Prüfe das Internet; ein VPN oder eine Firewall kann sie blockieren. Dateien funktionieren auch ohne sie. |
| **Free space** (Freier Speicher) ist knapp | Mach Platz auf der Festplatte: Ein 6-Stunden-Stream braucht während der Verarbeitung etwa 20 GB. |
| **Speech to text** (Sprache zu Text): ein Modell ist nicht heruntergeladen | Es lädt sich beim ersten Auftrag von selbst herunter; oder drücke **Download** in **Settings → Speech to text**. |

Eine Behebung, die ein Administratorpasswort braucht, läuft nie unbemerkt: SMTV öffnet ein Terminal mit dem Befehl,
damit du siehst, was es tut.

## 2. Häufige Probleme

- **Ein Link funktioniert nicht.** Links brauchen das [StreamMoment-Konto](account.md). Kein Konto? Lade die Aufnahme
  selbst herunter und gib SMTV die Datei.
- **Keine Clips oder sehr wenige.** SMTV behält nur die Momente, die die KI als gut bewertet hat. Ein kurzer oder
  ruhiger Stream ergibt vielleicht wenige. Eine kostenlose KI auf deinem Computer findet weniger gute Momente als eine
  aus der Cloud.
- **«Too many requests»** (zu viele Anfragen). Der kostenlose Tarif deines KI-Dienstes hat sein Limit erreicht: warte
  oder nutze einen bezahlten Tarif oder das Konto.
- **Das Handy öffnet SMTV nicht.** Dasselbe WLAN, kein VPN, SMTV in der Firewall erlauben – siehe [Handy](phone.md).
- **Windows: Ein Terminal verweigert `smtv`.** Das ist die Intelligente App-Steuerung (Smart App Control); starte SMTV
  über sein Symbol.
- **Das Fenster hat die Verbindung zu SMTV verloren.** Schließe das Fenster und öffne SMTV erneut.

Ein angehaltener Auftrag kann weiterlaufen: Drücke **Continue** (Fortsetzen) – SMTV macht beim selben Schritt weiter
und wiederholt nicht, was schon erledigt ist.

## 3. Ein Problem melden

Kommst du trotzdem nicht weiter? Sag es uns – das hilft allen.

1. **Settings → Computer check → Report a problem** (Problem melden; der Knopf **Report…**, er ist auch in
   **Settings → About**), oder der Knopf unter einem fehlgeschlagenen Auftrag.
2. SMTV zeigt, was in den Bericht kommt: Versionen, die Computerprüfung, Einstellungen und Logs. **Schlüssel und
   Tokens werden herausgeschnitten**, dein Benutzerordner erscheint als `~`. Links und Dateinamen bleiben draußen, außer
   du setzt das Häkchen.
3. Drücke **Save and open GitHub** (Speichern und GitHub öffnen). SMTV speichert das Archiv, und im Browser öffnet sich
   ein neues Issue mit ausgefüllter Zusammenfassung. Zieh das Archiv hinein und drücke **Submit**.

SMTV sendet nichts von selbst. Ohne das Fenster: Führe `smtv report` in einem Terminal aus. Du kannst auch direkt
[ein Issue eröffnen](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml).
