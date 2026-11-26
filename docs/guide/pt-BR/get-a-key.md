<!-- languages -->
[Русский](../get-a-key.md) · [English](../en/get-a-key.md) · [Қазақша](../kk/get-a-key.md) · [Oʻzbekcha](../uz/get-a-key.md) · [Azərbaycanca](../az/get-a-key.md) · [Кыргызча](../ky/get-a-key.md) · [简体中文](../zh-CN/get-a-key.md) · [日本語](../ja/get-a-key.md) · [한국어](../ko/get-a-key.md) · [Tiếng Việt](../vi/get-a-key.md) · [Bahasa Indonesia](../id/get-a-key.md) · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · [Español](../es/get-a-key.md) · **Português** · [Deutsch](../de/get-a-key.md)

> 🌐 Esta página foi traduzida automaticamente. Ajude a melhorá-la: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [Original: Русский](../get-a-key.md).

# Onde conseguir uma chave

Uma **chave** (uma «API key», chave de API) é uma senha longa que deixa o SMTV usar um serviço de IA em seu nome. Você
a recebe no site do serviço depois de se cadastrar. O SMTV a guarda só no seu computador e a envia só para esse
serviço; ela nunca aparece em logs nem em relatórios de problema.

> Preços e planos grátis mudam. O que está escrito aqui foi conferido nas páginas dos próprios serviços em **23.11.2026** — confira na página do
> serviço antes de começar.

## Qual serviço

| Serviço | Plano grátis | Onde pegar a chave | Bom saber |
|---|---|---|---|
| **Google Gemini** | Sim, com limites por minuto e por dia; os modelos grátis estão listados na página de preços do Google | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | O começo grátis mais fácil; a cobrança só é configurada para o plano pago. No plano grátis, o Google pode usar o que você envia para melhorar os produtos dele e pessoas podem ler — exceto no EEE, na Suíça e no Reino Unido. Não está disponível em todos os países (não na Rússia, por exemplo): veja a lista de regiões do Google. |
| **Groq** | Sim, com limites mostrados no console dele | [console.groq.com/keys](https://console.groq.com/keys) | Muito rápido. Também faz fala em texto na nuvem, barato (cerca de $0.04 por hora de áudio com Whisper large-v3 turbo). |
| **OpenRouter** | Modelos cujo nome termina em `:free`: 20 requisições por minuto, 50 por dia (1.000 por dia depois que você compra $10 de crédito) | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | Uma chave para centenas de modelos de empresas diferentes. 50 requisições por dia não bastam para uma transmissão longa. |
| **Mistral** | Confira no site: as páginas dele não informavam condições grátis para a API | [console.mistral.ai](https://console.mistral.ai) | Uma empresa europeia. |
| **DeepSeek** | Não | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | Pago a partir de um saldo que você recarrega antes. |
| **OpenAI** | Não se promete crédito grátis: uma conta nova paga adiantado, a partir de $5 | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Os modelos por trás do ChatGPT. A assinatura do ChatGPT não é a mesma coisa que uma chave: a chave é paga à parte. Só em países compatíveis (não na Rússia). |
| **Claude (Anthropic)** | Não | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | A assinatura do Claude não é a mesma coisa que uma chave. Só em regiões compatíveis (não na Rússia). |

O SMTV também conhece xAI, Together, Fireworks, Qwen, Kimi, GLM, Cerebras e qualquer endereço compatível com OpenAI —
veja [para usuários avançados](../../advanced.md#ai-services-and-keys).

**Um plano grátis tem limites.** Uma live longa envia muitos pedidos; quando o limite é atingido, o serviço responde
«too many requests» (pedidos demais) e o SMTV espera ou para. Para uma live de 6–12 horas, um plano pago ou a
[conta](account.md) funciona melhor.

## Exemplo: uma chave grátis do Gemini, passo a passo

1. Abra [aistudio.google.com/apikey](https://aistudio.google.com/apikey) e entre com uma conta Google.
2. Aceite os termos, se for pedido.
3. Clique em **Criar chave de API** (Create API key). Copie a chave (ela começa com `AIza…`). Guarde em segredo, como
   uma senha.
4. No SMTV: **Settings → AI → Your own key → Add a key** (Configurações → IA → Sua própria chave → Adicionar uma
   chave).
5. Escolha **Gemini**, cole a chave, clique em **Check** (Verificar). O SMTV diz se a chave funciona.
6. Pronto. Cada etapa da IA agora usa o Gemini com um modelo adequado; **Settings → AI steps** (etapas da IA) mostra
   qual.

Os outros serviços funcionam do mesmo jeito: cadastre-se, encontre **API keys**, crie uma, cole no SMTV, clique em
**Check**. Serviços pagos primeiro pedem para você adicionar um cartão ou colocar saldo.

## Sua chave está segura

- Guardada no seu computador, criptografada.
- Enviada só para o serviço a que pertence. O StreamMoment nunca a vê.
- Perdeu ou vazou? Apague no site do serviço e crie uma nova.
