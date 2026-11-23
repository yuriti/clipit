<!-- languages -->
[English](../get-a-key.md) · [Русский](../ru/get-a-key.md) · [Қазақша](../kk/get-a-key.md) · [Oʻzbekcha](../uz/get-a-key.md) · [Azərbaycanca](../az/get-a-key.md) · [Кыргызча](../ky/get-a-key.md) · [简体中文](../zh-CN/get-a-key.md) · **日本語** · [한국어](../ko/get-a-key.md) · [Tiếng Việt](../vi/get-a-key.md) · [Bahasa Indonesia](../id/get-a-key.md) · [हिन्दी](../hi/get-a-key.md) · [বাংলা](../bn/get-a-key.md) · [Español](../es/get-a-key.md) · [Português](../pt-BR/get-a-key.md) · [Deutsch](../de/get-a-key.md)

> 🌐 このページは自動翻訳されています。改善にご協力ください：[Weblate](https://hosted.weblate.org/engage/smtv/) · [プルリクエスト](https://github.com/streammomenttv/smtv/pulls)。

# キーの入手先

**キー**（「API キー」）は、SMTV があなたの代わりに AI サービスを使うための長いパスワードです。サービスに登録すると、そのサイトで手に入ります。
SMTV はそれをあなたのパソコンにだけ保存し、そのサービスにだけ送ります。ログや問題レポートに載ることはありません。

> 料金や無料プランは変わります。ここに書いてある内容は、各サービス自身のページで **23.11.2026** に確認したものです——始める前にサービスのページを確認してください。

## どのサービスにするか

| サービス | 無料プラン | キーの入手先 | 知っておくと便利 |
|---|---|---|---|
| **Google Gemini** | あり、1 分あたり・1 日あたりの上限付き。無料のモデルは Google の料金ページに載っています | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | 無料で始めるならいちばん簡単。支払い設定が必要なのは有料プランだけです。無料プランでは、送った内容を Google が自社製品の改善に使うことがあり、人が読むこともあります——欧州経済領域、スイス、英国を除きます。すべての国で使えるわけではありません（たとえばロシアでは使えません）：Google の対応地域の一覧を見てください。 |
| **Groq** | あり、上限付き。上限はコンソールで確認できます | [console.groq.com/keys](https://console.groq.com/keys) | とても速い。クラウドでの文字起こしも安くできます（Whisper large-v3 turbo で、音声 1 時間あたり約 $0.04）。 |
| **OpenRouter** | 名前の末尾が `:free` のモデル：1 分あたり 20 リクエスト、1 日あたり 50 リクエスト（$10 分のクレジットを購入すると 1 日 1,000） | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | ひとつのキーで、さまざまな会社の数百のモデルが使えます。長い配信には 1 日 50 リクエストでは足りません。 |
| **Mistral** | サイトで確認してください：ページには API の無料条件が書かれていませんでした | [console.mistral.ai](https://console.mistral.ai) | ヨーロッパの会社です。 |
| **DeepSeek** | なし | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | 先にチャージした残高から支払います。 |
| **OpenAI** | 無料クレジットは約束されていません：新しいアカウントは前払いで、$5 から | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | ChatGPT を動かしているモデル。ChatGPT のサブスクリプションとキーは別物です：キーは別に支払います。対応している国のみ（ロシアは不可）。 |
| **Claude (Anthropic)** | なし | [platform.claude.com/settings/keys](https://platform.claude.com/settings/keys) | Claude のサブスクリプションとキーは別物です。対応している地域のみ（ロシアは不可）。 |

SMTV は xAI、Together、Fireworks、Qwen、Kimi、GLM、Cerebras、そして OpenAI 互換のあらゆるアドレスにも対応しています——
[上級者向け](../../advanced.md#ai-services-and-keys)を見てください。

**無料プランには上限があります。** 長い配信は多くのリクエストを送ります。上限に達するとサービスは「リクエストが多すぎます」（«too many requests»）と返し、
SMTV は待つか停止します。6〜12 時間の配信なら、有料プランか[アカウント](account.md)のほうがうまくいきます。

## 例：無料の Gemini キーをステップごとに

1. [aistudio.google.com/apikey](https://aistudio.google.com/apikey) を開き、Google アカウントでログインします。
2. 求められたら規約に同意します。
3. **Create API key** を押します。キーをコピーします（`AIza…` で始まります）。パスワードと同じように秘密にしてください。
4. SMTV で：**Settings → AI → Your own key → Add a key**（設定 → AI → 自分のキー → キーを追加）。
5. **Gemini** を選び、キーを貼り付けて **Check**（確認）を押します。キーが使えるかどうか SMTV が教えてくれます。
6. 完了。これで AI のすべてのステップが、適したモデルで Gemini を使います。どのモデルかは **Settings → AI steps**（設定 → AI のステップ）で確認できます。

ほかのサービスも同じです：登録して、**API keys** を探し、キーを作成して SMTV に貼り付け、**Check** を押します。
有料サービスでは、先にカードの登録か残高のチャージを求められます。

## キーは安全です

- 暗号化してあなたのパソコンに保存されます。
- そのキーのサービスにだけ送られます。StreamMoment から見えることはありません。
- なくした、漏れた？サービスのサイトで削除して、新しいものを作ってください。
