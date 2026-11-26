<!-- languages -->
[Русский](../speech-and-languages.md) · [English](../en/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · **Español** · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 Esta página se tradujo automáticamente. Ayuda a mejorarla: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [Original: Русский](../speech-and-languages.md).

# Voz e idiomas

Primero SMTV convierte la voz del stream en texto, con el momento de cada palabra: así la IA entiende qué pasó. Esto
funciona **en tu computadora, gratis**. SMTV detecta el idioma del stream por sí mismo.

| Idioma | Modelo | Descarga (una vez) | Velocidad en un procesador de 12 núcleos |
|---|---|---|---|
| Ruso | GigaAM-v3, hecho para el ruso | 0.9 GB | 54× más rápido que el tiempo real |
| 25 idiomas europeos: inglés, español, alemán, francés, italiano, portugués, polaco, ucraniano y otros | Parakeet-TDT v3 | 2.4 GB | 33× más rápido que el tiempo real |
| Todos los demás idiomas: chino, japonés, coreano, hindi, bengalí, kazajo, uzbeko, azerbaiyano, vietnamita, indonesio y decenas más | Whisper large-v3-turbo | 1.6 GB | Aún no medido |

Un modelo se descarga solo la primera vez que llega un stream en su idioma. No hace falta tarjeta gráfica; una tarjeta
NVIDIA lo hace más rápido. En una Mac, Whisper funciona en el procesador y es más lento.

**Settings → Speech to text** (Configuración → Voz a texto) muestra cada modelo: dónde funciona, sus idiomas, tamaño y
velocidad, con **Download** (Descargar) y **Remove** (Quitar). Ahí cada idioma puede usar otro modelo, también
**Whisper in the cloud** (Whisper en la nube) con tu propia clave (Groq u OpenAI): más rápido en una computadora
modesta, pero entonces el audio sale de tu computadora.

<img src="../../images/speech.png" alt="Settings → Speech to text: los modelos y los idiomas que manejan" width="820">

**El idioma de la ventana** es aparte: SMTV habla el idioma de tu computadora; **Settings → Language and theme**
(Configuración → Idioma y tema) elige otro. ¿Falta tu idioma o está a medio traducir? [Ayuda a traducirlo](../../translations.md):
no hace falta saber programar.
