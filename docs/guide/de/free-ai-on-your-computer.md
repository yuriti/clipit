<!-- languages -->
[English](../free-ai-on-your-computer.md) · [Русский](../ru/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · **Deutsch**

> 🌐 Diese Seite wurde automatisch übersetzt. Hilf mit, sie zu verbessern: [Weblate](https://hosted.weblate.org/engage/smtv/) · [Pull Request](https://github.com/streammomenttv/smtv/pulls).

# Eine kostenlose KI auf deinem Computer

Die KI kann direkt auf deinem Computer laufen, kostenlos: Nichts verlässt ihn, und es gibt nichts zu bezahlen. Du
brauchst ein Programm, das KI-Modelle ausführt – **Ollama** oder **LM Studio** – und ein Modell, zum Beispiel **Qwen**.
SMTV findet das Programm von selbst.

**Ehrlich gesagt:** Modelle, die auf einen Heimcomputer passen, sind schwächer als die in der Cloud, deshalb werden die
Clips schlechter, und keines der empfohlenen Modelle wurde bisher mit SMTV getestet. Wenn dich das Ergebnis
enttäuscht, probier das [Konto](account.md) oder [einen Schlüssel](get-a-key.md).

## 1. Welches Modell zu deinem Computer passt

Entscheidend ist der **Grafikspeicher** deiner Grafikkarte (auf einem Mac mit Apple Silicon: der gesamte Arbeitsspeicher).

| Grafikspeicher | Modell | Download | Hinweise |
|---|---|---|---|
| weniger als 8 GB | — | — | Zu wenig: Nutze das Konto oder einen Schlüssel |
| 8 GB | `qwen3:8b` | 5,2 GB | Das leichteste, das gut genug funktioniert |
| 10–12 GB | `qwen3-vl:8b` oder `gemma3:12b` | 6,1 / 8,1 GB | Diese schauen sich auch Bilder aus dem Video an |
| 16 GB und mehr | `qwen3:14b` | 9,3 GB | Das beste der vier |

Modelle kleiner als 7B («7 Milliarden») werden nicht empfohlen: Sie verderben die Antworten, die SMTV braucht.

**So findest du deinen Grafikspeicher:**
- **Windows:** drücke Strg+Umschalt+Esc → **Leistung** (Performance) → **GPU** → **Dedizierter GPU-Speicher** (Dedicated GPU memory).
- **Mac:** Apple-Menü → **Über diesen Mac** (About This Mac) → **Speicher** (Memory). Ein Mac teilt den Speicher mit der
  KI: Bei 16 GB nimm `qwen3:8b`, bei 32 GB oder mehr `qwen3:14b`.

## 2a. Ollama (am einfachsten)

1. Lade Ollama von [ollama.com/download](https://ollama.com/download) herunter und installiere es wie jedes Programm.
   Es startet von selbst und sitzt neben der Uhr.
2. In SMTV: **Settings → AI → Free, on this computer → Find on this computer** (Einstellungen → KI → Kostenlos, auf
   diesem Computer → Auf diesem Computer suchen). SMTV findet Ollama.
3. Öffne **Ollama** in der Liste: SMTV zeigt die empfohlenen Modelle mit ihrer Größe. Drücke **Download** neben dem
   aus der Tabelle oben und warte (5–10 GB).
4. Fertig. SMTV wählt dieses Modell von selbst für seine Schritte.

SMTV stellt den Speicher von Ollama für jeden Auftrag so ein, dass der ganze Text des Streams hineinpasst; du musst die
Einstellungen von Ollama nicht ändern.

## 2b. LM Studio

1. Lade LM Studio von [lmstudio.ai/download](https://lmstudio.ai/download) herunter und installiere es.
2. Öffne in LM Studio **Discover**, suche nach **Qwen3 8B** (oder 14B, laut Tabelle) und drücke **Download**.
3. Öffne den Tab **Developer** und schalte **Start server** ein (er lauscht auf Port 1234). Lade dort das Modell.
4. In SMTV: **Settings → AI → Free, on this computer → Find on this computer**. SMTV findet LM Studio.

## 3. Einen Clip machen

Gib SMTV eine [Videodatei](first-clip.md). Ein Link zu Twitch oder YouTube braucht auch mit einer kostenlosen KI das
[Konto](account.md): Das Konto holt die Aufnahme.

Die kostenlose KI arbeitet langsamer als eine aus der Cloud; ein langer Stream kann ein paar Stunden dauern. Lass den
Computer an.
