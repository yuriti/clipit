<!-- languages -->
[Русский](../speech-and-languages.md) · [English](../en/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · **Deutsch**

> 🌐 Diese Seite wurde automatisch übersetzt. Hilf mit, sie zu verbessern: [Weblate](https://hosted.weblate.org/engage/smtv/) · [Pull Request](https://github.com/yuriti/clipit/pulls) · [Original: Русский](../speech-and-languages.md).

# Sprache und Sprachen

Zuerst wandelt SMTV die Sprache des Streams in Text um, mit der Zeit jedes Wortes – so versteht die KI, was passiert
ist. Das läuft **auf deinem Computer, kostenlos**. SMTV erkennt die Sprache des Streams von selbst.

| Sprache | Modell | Download (einmalig) | Geschwindigkeit auf einem 12-Kern-Prozessor |
|---|---|---|---|
| Russisch | GigaAM-v3, für Russisch gemacht | 0,9 GB | 54-mal schneller als Echtzeit |
| 25 europäische Sprachen: Englisch, Spanisch, Deutsch, Französisch, Italienisch, Portugiesisch, Polnisch, Ukrainisch und andere | Parakeet-TDT v3 | 2,4 GB | 33-mal schneller als Echtzeit |
| Alle anderen Sprachen: Chinesisch, Japanisch, Koreanisch, Hindi, Bengalisch, Kasachisch, Usbekisch, Aserbaidschanisch, Vietnamesisch, Indonesisch und Dutzende weitere | Whisper large-v3-turbo | 1,6 GB | Noch nicht gemessen |

Ein Modell lädt sich von selbst herunter, wenn zum ersten Mal ein Stream in seiner Sprache kommt. Eine Grafikkarte ist
nicht nötig; eine NVIDIA-Karte macht es schneller. Auf einem Mac läuft Whisper auf dem Prozessor und ist langsamer.

**Settings → Speech to text** (Einstellungen → Sprache zu Text) zeigt jedes Modell: wo es läuft, seine Sprachen, Größe
und Geschwindigkeit, mit **Download** und **Remove** (Entfernen). Dort kann jede Sprache ein anderes Modell bekommen,
auch **Whisper in the cloud** (Whisper in der Cloud) mit deinem eigenen Schlüssel (Groq oder OpenAI) – schneller auf
einem schwachen Computer, aber dann verlässt der Ton deinen Computer.

<img src="../../images/speech.png" alt="Settings → Speech to text: die Modelle und die Sprachen, die sie übernehmen" width="820">

**Die Sprache des Fensters** ist davon getrennt: SMTV spricht die Sprache deines Computers; **Settings → Language and
theme** (Einstellungen → Sprache und Design) wählt eine andere. Deine Sprache fehlt oder ist nur halb übersetzt?
[Hilf beim Übersetzen](../../translations.md) – ohne Programmieren.
