<!-- languages -->
[Русский](../get-a-key.md) · [English](../en/get-a-key.md) · [Қазақша](../kk/get-a-key.md) · [Oʻzbekcha](../uz/get-a-key.md) · [Azərbaycanca](../az/get-a-key.md) · [Кыргызча](../ky/get-a-key.md) · [简体中文](../zh-CN/get-a-key.md) · [日本語](../ja/get-a-key.md) · [한국어](../ko/get-a-key.md) · [Tiếng Việt](../vi/get-a-key.md) · [Bahasa Indonesia](../id/get-a-key.md) · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · **Español** · [Português](../pt-BR/get-a-key.md) · [Deutsch](../de/get-a-key.md)

> 🌐 Esta página se tradujo automáticamente. Ayuda a mejorarla: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Original: Русский](../get-a-key.md).

# Dónde conseguir una clave

Una **clave** (una «API key») es una contraseña larga que permite a SMTV usar un servicio de IA en tu nombre. La
consigues en el sitio del servicio después de registrarte. SMTV la guarda solo en tu computadora y la envía solo a ese
servicio; nunca aparece en registros ni en reportes de problemas.

> Los precios y los planes gratuitos cambian. Lo que dice aquí se comprobó en las páginas de los propios servicios el **23.11.2026**: revisa la página del servicio antes de empezar.

## Qué servicio

| Servicio | Plan gratuito | Dónde conseguir la clave | Bueno saber |
|---|---|---|---|
| **Google Gemini** | Sí, con límites por minuto y por día; los modelos gratuitos aparecen en la página de precios de Google | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | El inicio gratuito más fácil; la facturación solo se configura para el plan de pago. En el plan gratuito, Google puede usar lo que envías para mejorar sus productos y es posible que personas lo lean, salvo en el EEE, Suiza y el Reino Unido. No está disponible en todos los países (por ejemplo, no en Rusia): consulta la lista de regiones de Google. |
| **Groq** | Sí, con límites que se ven en su consola | [console.groq.com/keys](https://console.groq.com/keys) | Muy rápido. También puede convertir voz a texto en la nube, a bajo costo (unos $0.04 por hora de audio con Whisper large-v3 turbo). |
| **OpenRouter** | Modelos cuyo nombre termina en `:free`: 20 solicitudes por minuto, 50 por día (1.000 por día cuando has comprado $10 de crédito) | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | Una clave para cientos de modelos de distintas empresas. 50 solicitudes por día no alcanzan para un stream largo. |
| **Mistral** | Compruébalo en su sitio: sus páginas no indicaban condiciones gratuitas para la API | [console.mistral.ai](https://console.mistral.ai) | Una empresa europea. |
| **DeepSeek** | No | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | Se paga con un saldo que recargas antes. |
| **OpenAI** | No se promete crédito gratuito: una cuenta nueva paga por adelantado, desde $5 | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Los modelos detrás de ChatGPT. Una suscripción de ChatGPT no es lo mismo que una clave: la clave se paga aparte. Solo en países compatibles (no en Rusia). |
| **Claude (Anthropic)** | No | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | Una suscripción de Claude no es lo mismo que una clave. Solo en regiones compatibles (no en Rusia). |

SMTV también conoce xAI, Together, Fireworks, Qwen, Kimi, GLM, Cerebras y cualquier dirección compatible con OpenAI;
mira [para usuarios avanzados](../../advanced.md#ai-services-and-keys).

**Un plan gratuito tiene límites.** Un stream largo envía muchas solicitudes; cuando se alcanza el límite, el servicio
responde «too many requests» (demasiadas solicitudes) y SMTV espera o se detiene. Para un stream de 6–12 horas
funciona mejor un plan de pago o la [cuenta](account.md).

## Ejemplo: una clave gratuita de Gemini, paso a paso

1. Abre [aistudio.google.com/apikey](https://aistudio.google.com/apikey) e inicia sesión con una cuenta de Google.
2. Acepta los términos si te lo piden.
3. Presiona **Create API key**. Copia la clave (empieza con `AIza…`). Guárdala en secreto, como una contraseña.
4. En SMTV: **Settings → AI → Your own key → Add a key** (Configuración → IA → Tu propia clave → Agregar una clave).
5. Elige **Gemini**, pega la clave y presiona **Check** (Comprobar). SMTV te dice si la clave funciona.
6. Listo. Cada paso de la IA ahora usa Gemini con un modelo adecuado; **Settings → AI steps** (Configuración → Pasos de
   la IA) muestra cuál.

Los demás servicios funcionan igual: regístrate, busca **API keys**, crea una, pégala en SMTV y presiona **Check**. Los
servicios de pago primero te piden agregar una tarjeta o recargar saldo.

## Tu clave está segura

- Se guarda en tu computadora, cifrada.
- Se envía solo al servicio al que pertenece. StreamMoment nunca la ve.
- ¿La perdiste o se filtró? Bórrala en el sitio del servicio y crea una nueva.
