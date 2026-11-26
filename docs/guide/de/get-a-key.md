<!-- languages -->
[Русский](../get-a-key.md) · [English](../en/get-a-key.md) · [Қазақша](../kk/get-a-key.md) · [Oʻzbekcha](../uz/get-a-key.md) · [Azərbaycanca](../az/get-a-key.md) · [Кыргызча](../ky/get-a-key.md) · [简体中文](../zh-CN/get-a-key.md) · [日本語](../ja/get-a-key.md) · [한국어](../ko/get-a-key.md) · [Tiếng Việt](../vi/get-a-key.md) · [Bahasa Indonesia](../id/get-a-key.md) · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · [Español](../es/get-a-key.md) · [Português](../pt-BR/get-a-key.md) · **Deutsch**

> 🌐 Diese Seite wurde automatisch übersetzt. Hilf mit, sie zu verbessern: [Weblate](https://hosted.weblate.org/engage/smtv/) · [Pull Request](https://github.com/streammomenttv/smtv/pulls) · [Original: Русский](../get-a-key.md).

# Wo man einen Schlüssel bekommt

Ein **Schlüssel** (ein «API-Schlüssel») ist ein langes Passwort, mit dem SMTV einen KI-Dienst in deinem Namen nutzen
kann. Du bekommst ihn auf der Website des Dienstes nach der Registrierung. SMTV speichert ihn nur auf deinem Computer
und sendet ihn nur an diesen Dienst; er taucht nie in Logs oder Problemberichten auf.

> Preise und kostenlose Tarife ändern sich. Was hier steht, wurde am **23.11.2026** auf den Seiten der Dienste selbst geprüft – prüfe die Seite des Dienstes, bevor du anfängst.

## Welcher Dienst

| Dienst | Kostenloser Tarif | Wo man den Schlüssel bekommt | Gut zu wissen |
|---|---|---|---|
| **Google Gemini** | Ja, mit Limits pro Minute und pro Tag; die kostenlosen Modelle stehen auf der Preisseite von Google | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Der leichteste kostenlose Einstieg; die Abrechnung wird nur für den bezahlten Tarif eingerichtet. Im kostenlosen Tarif darf Google das, was du sendest, zur Verbesserung seiner Produkte nutzen, und Menschen können es lesen – außer im EWR, in der Schweiz und im Vereinigten Königreich. Nicht in jedem Land verfügbar (zum Beispiel nicht in Russland): siehe die Regionenliste von Google. |
| **Groq** | Ja, mit Limits, die in der Konsole angezeigt werden | [console.groq.com/keys](https://console.groq.com/keys) | Sehr schnell. Kann auch Sprache zu Text in der Cloud, günstig (etwa $0.04 pro Stunde Audio mit Whisper large-v3 turbo). |
| **OpenRouter** | Modelle, deren Name auf `:free` endet: 20 Anfragen pro Minute, 50 pro Tag (1.000 pro Tag, sobald du Guthaben für $10 gekauft hast) | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | Ein Schlüssel für Hunderte Modelle verschiedener Firmen. 50 Anfragen pro Tag reichen für einen langen Stream nicht. |
| **Mistral** | Prüfe auf der Website: Auf den Seiten waren keine kostenlosen Bedingungen für die API angegeben | [console.mistral.ai](https://console.mistral.ai) | Ein europäisches Unternehmen. |
| **DeepSeek** | Nein | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | Bezahlt wird von einem Guthaben, das du zuerst auflädst. |
| **OpenAI** | Kein kostenloses Guthaben versprochen: Ein neues Konto zahlt im Voraus, ab $5 | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Die Modelle hinter ChatGPT. Ein ChatGPT-Abo ist nicht dasselbe wie ein Schlüssel: Der Schlüssel wird separat bezahlt. Nur in unterstützten Ländern (nicht in Russland). |
| **Claude (Anthropic)** | Nein | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | Ein Claude-Abo ist nicht dasselbe wie ein Schlüssel. Nur in unterstützten Regionen (nicht in Russland). |

SMTV kennt auch xAI, Together, Fireworks, Qwen, Kimi, GLM, Cerebras und jede OpenAI-kompatible Adresse – siehe
[für Fortgeschrittene](../../advanced.md#ai-services-and-keys).

**Ein kostenloser Tarif hat Limits.** Ein langer Stream sendet viele Anfragen; ist das Limit erreicht, antwortet der
Dienst «too many requests» (zu viele Anfragen), und SMTV wartet oder hört auf. Für einen Stream von 6–12 Stunden
funktioniert ein bezahlter Tarif oder das [Konto](account.md) besser.

## Beispiel: ein kostenloser Gemini-Schlüssel, Schritt für Schritt

1. Öffne [aistudio.google.com/apikey](https://aistudio.google.com/apikey) und melde dich mit einem Google-Konto an.
2. Akzeptiere die Bedingungen, falls danach gefragt wird.
3. Drücke **Create API key** (API-Schlüssel erstellen). Kopiere den Schlüssel (er beginnt mit `AIza…`). Halte ihn
   geheim, wie ein Passwort.
4. In SMTV: **Settings → AI → Your own key → Add a key** (Einstellungen → KI → Eigener Schlüssel → Schlüssel hinzufügen).
5. Wähle **Gemini**, füge den Schlüssel ein, drücke **Check** (Prüfen). SMTV sagt, ob der Schlüssel funktioniert.
6. Fertig. Jeder KI-Schritt nutzt jetzt Gemini mit einem passenden Modell; **Settings → AI steps** (Einstellungen →
   KI-Schritte) zeigt, welches.

Andere Dienste funktionieren genauso: registrieren, **API keys** finden, einen erstellen, in SMTV einfügen, **Check**
drücken. Bezahlte Dienste verlangen zuerst, dass du eine Karte hinzufügst oder ein Guthaben auflädst.

## Dein Schlüssel ist sicher

- Auf deinem Computer gespeichert, verschlüsselt.
- Nur an den Dienst gesendet, zu dem er gehört. StreamMoment sieht ihn nie.
- Verloren oder geleakt? Lösche ihn auf der Website des Dienstes und erstelle einen neuen.
