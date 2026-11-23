<!-- languages -->
[English](../free-ai-on-your-computer.md) · [Русский](../ru/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · **Español** · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 Esta página se tradujo automáticamente. Ayuda a mejorarla: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls).

# Una IA gratuita en tu computadora

La IA puede funcionar directamente en tu computadora, gratis: no sale nada de ella y no hay nada que pagar. Necesitas un
programa que ejecute modelos de IA (**Ollama** o **LM Studio**) y un modelo, por ejemplo **Qwen**. SMTV encuentra el
programa por sí solo.

**Siendo honestos:** los modelos que caben en una computadora de casa son más débiles que los de la nube, así que los
clips salen peores, y ninguno de los modelos recomendados se ha probado todavía con SMTV. Si el resultado te
decepciona, prueba la [cuenta](account.md) o [una clave](get-a-key.md).

## 1. Qué modelo va con tu computadora

Lo que importa es la **memoria de video** de tu tarjeta gráfica (en una Mac con Apple silicon: toda la memoria).

| Memoria de video | Modelo | Descarga | Notas |
|---|---|---|---|
| menos de 8 GB | — | — | Demasiado poca: usa la cuenta o una clave |
| 8 GB | `qwen3:8b` | 5.2 GB | El más ligero que funciona lo bastante bien |
| 10–12 GB | `qwen3-vl:8b` o `gemma3:12b` | 6.1 / 8.1 GB | Estos también miran fotogramas del video |
| 16 GB o más | `qwen3:14b` | 9.3 GB | El mejor de los cuatro |

No se recomiendan modelos de menos de 7B («7 mil millones»): rompen las respuestas que SMTV necesita.

**Cómo saber cuánta memoria de video tienes:**
- **Windows:** presiona Ctrl+Shift+Esc → **Rendimiento** (Performance) → **GPU** → **Memoria dedicada de GPU**
  (Dedicated GPU memory).
- **Mac:** menú Apple → **Acerca de esta Mac** (About This Mac) → **Memoria** (Memory). Una Mac comparte la memoria con
  la IA: con 16 GB elige `qwen3:8b`, con 32 GB o más `qwen3:14b`.

## 2a. Ollama (lo más sencillo)

1. Descarga Ollama desde [ollama.com/download](https://ollama.com/download) e instálalo como cualquier programa. Se
   inicia solo y vive junto al reloj.
2. En SMTV: **Settings → AI → Free, on this computer → Find on this computer** (Configuración → IA → Gratis, en esta
   computadora → Buscar en esta computadora). SMTV encuentra Ollama.
3. Abre **Ollama** en la lista: SMTV muestra los modelos recomendados con su tamaño. Presiona **Download** (Descargar)
   junto al de la tabla de arriba y espera (5–10 GB).
4. Listo. SMTV elige ese modelo para sus pasos por sí solo.

SMTV ajusta la memoria de Ollama en cada solicitud para que quepa todo el texto del stream; no necesitas cambiar la
configuración de Ollama.

## 2b. LM Studio

1. Descarga LM Studio desde [lmstudio.ai/download](https://lmstudio.ai/download) e instálalo.
2. En LM Studio abre **Discover**, busca **Qwen3 8B** (o 14B, según la tabla) y presiona **Download**.
3. Abre la pestaña **Developer** y activa **Start server** (escucha en el puerto 1234). Carga ahí el modelo.
4. En SMTV: **Settings → AI → Free, on this computer → Find on this computer**. SMTV encuentra LM Studio.

## 3. Haz un clip

Dale a SMTV un [archivo de video](first-clip.md). Un enlace a Twitch o YouTube necesita la [cuenta](account.md)
incluso con una IA gratuita: la cuenta es la que descarga la grabación.

La IA gratuita trabaja más lento que una en la nube; un stream largo puede tardar unas horas. Deja la computadora
encendida.
