<!-- languages -->
[English](../get-a-key.md) · [Русский](../ru/get-a-key.md) · [Қазақша](../kk/get-a-key.md) · [Oʻzbekcha](../uz/get-a-key.md) · [Azərbaycanca](../az/get-a-key.md) · [Кыргызча](../ky/get-a-key.md) · **简体中文** · [日本語](../ja/get-a-key.md) · [한국어](../ko/get-a-key.md) · [Tiếng Việt](../vi/get-a-key.md) · [Bahasa Indonesia](../id/get-a-key.md) · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · [Español](../es/get-a-key.md) · [Português](../pt-BR/get-a-key.md) · [Deutsch](../de/get-a-key.md)

> 🌐 本页面由机器自动翻译。欢迎帮助改进：[Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls)。

# 去哪里获取密钥

**密钥**（“API 密钥”）是一串长密码，让 SMTV 能以你的名义使用某个 AI 服务。注册后，你可以在该服务的网站上获取它。
SMTV 只把它保存在你的电脑上，也只发送给那个服务；它永远不会出现在日志或问题报告里。

> 价格和免费套餐会变化。这里写的内容已于 **23.11.2026** 在各服务自己的页面上核对过——开始之前请再看一下该服务的页面。

## 选哪个服务

| 服务 | 免费套餐 | 在哪里获取密钥 | 需要知道的 |
|---|---|---|---|
| **Google Gemini** | 有，每分钟和每天都有限额；免费模型列在 Google 的价格页面上 | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | 最容易的免费入门方式；只有付费套餐才需要设置付款。在免费套餐下，Google 可能会用你发送的内容来改进它的产品，而且可能有人会阅读——欧洲经济区、瑞士和英国除外。并非每个国家都能用（例如俄罗斯不行）：请看 Google 的地区列表。 |
| **Groq** | 有，有限额，限额显示在它的控制台里 | [console.groq.com/keys](https://console.groq.com/keys) | 非常快。也能在云端做语音转文字，价格便宜（用 Whisper large-v3 turbo，每小时音频约 $0.04）。 |
| **OpenRouter** | 名称以 `:free` 结尾的模型：每分钟 20 次请求，每天 50 次（买过 $10 额度后每天 1,000 次） | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | 一个密钥就能用不同公司的数百个模型。每天 50 次请求，对长直播来说不够。 |
| **Mistral** | 请到它的网站确认：它的页面上没有写明 API 的免费条件 | [console.mistral.ai](https://console.mistral.ai) | 一家欧洲公司。 |
| **DeepSeek** | 没有 | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | 从你先充值的余额里扣费。 |
| **OpenAI** | 不承诺免费额度：新账号要先付款，起步 $5 | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | ChatGPT 背后的模型。ChatGPT 订阅和密钥不是一回事：密钥要单独付费。仅限受支持的国家（俄罗斯不行）。 |
| **Claude (Anthropic)** | 没有 | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | Claude 订阅和密钥不是一回事。仅限受支持的地区（俄罗斯不行）。 |

SMTV 还支持 xAI、Together、Fireworks、Qwen、Kimi、GLM、Cerebras 以及任何兼容 OpenAI 的地址——见
[给高级用户](../../advanced.md#ai-services-and-keys)。

**免费套餐有限额。** 一场长直播会发出很多请求；达到限额后，服务会回复“请求过多”（«too many requests»），SMTV 会等待或停止。
对于 6–12 小时的直播，付费套餐或[账户](account.md)效果更好。

## 示例：一步一步获取免费的 Gemini 密钥

1. 打开 [aistudio.google.com/apikey](https://aistudio.google.com/apikey)，用 Google 账号登录。
2. 如果要求，接受条款。
3. 点 **Create API key**。复制密钥（以 `AIza…` 开头）。像对待密码一样保密。
4. 在 SMTV 中：**Settings → AI → Your own key → Add a key**（设置 → AI → 你自己的密钥 → 添加密钥）。
5. 选择 **Gemini**，粘贴密钥，点 **Check**（检查）。SMTV 会告诉你密钥是否可用。
6. 完成。现在 AI 的每一步都会使用 Gemini 及合适的模型；**Settings → AI steps**（设置 → AI 步骤）里能看到具体是哪个。

其他服务也是一样：注册，找到 **API keys**，创建一个，粘贴到 SMTV，点 **Check**。
付费服务会先要求你绑定银行卡或充值余额。

## 你的密钥是安全的

- 加密保存在你的电脑上。
- 只发送给它所属的服务。StreamMoment 永远看不到它。
- 丢了或泄露了？在服务的网站上删除它，再创建一个新的。
