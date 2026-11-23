<!-- languages -->
[English](../free-ai-on-your-computer.md) · [Русский](../ru/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · **日本語** · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 このページは自動翻訳されています。改善にご協力ください：[Weblate](https://hosted.weblate.org/engage/smtv/) · [プルリクエスト](https://github.com/streammomenttv/smtv/pulls)。

# パソコンで動く無料 AI

AI はあなたのパソコンで直接、無料で動かせます：何も外に出ず、支払いも一切ありません。必要なのは AI モデルを動かすプログラム——
**Ollama** または **LM Studio**——と、モデル（たとえば **Qwen**）です。SMTV はそのプログラムを自動で見つけます。

**正直に言うと：** 家庭用パソコンで動くモデルはクラウドのものより弱いので、クリップの出来は落ちます。また、おすすめのモデルはどれも
まだ SMTV と一緒にテストしていません。結果にがっかりしたら、[アカウント](account.md)か[キー](get-a-key.md)を試してください。

## 1. パソコンに合うモデル

大事なのはグラフィックボードの**ビデオメモリ**です（Apple シリコン搭載の Mac ではメモリ全体）。

| ビデオメモリ | モデル | ダウンロード | メモ |
|---|---|---|---|
| 8 GB 未満 | — | — | 足りません：アカウントかキーを使ってください |
| 8 GB | `qwen3:8b` | 5.2 GB | 十分に使える中でいちばん軽い |
| 10〜12 GB | `qwen3-vl:8b` または `gemma3:12b` | 6.1 / 8.1 GB | 動画のフレームも見ます |
| 16 GB 以上 | `qwen3:14b` | 9.3 GB | 4 つの中で最良 |

7B（「70 億」）より小さいモデルはおすすめしません：SMTV が必要とする回答を崩してしまいます。

**ビデオメモリの確かめ方：**
- **Windows：** Ctrl+Shift+Esc を押す →「パフォーマンス」（**Performance**）→ **GPU** →「専用 GPU メモリ」（**Dedicated GPU memory**）。
- **Mac：** アップルメニュー →「この Mac について」（**About This Mac**）→「メモリ」（**Memory**）。Mac はメモリを AI と共有します：
  16 GB なら `qwen3:8b`、32 GB 以上なら `qwen3:14b`。

## 2a. Ollama（いちばん簡単）

1. [ollama.com/download](https://ollama.com/download) から Ollama をダウンロードし、ほかのプログラムと同じようにインストールします。
   自動で起動し、時計の近くに常駐します。
2. SMTV で：**Settings → AI → Free, on this computer → Find on this computer**（設定 → AI → 無料、このパソコンで → このパソコンで探す）。SMTV が Ollama を見つけます。
3. リストの **Ollama** を開きます：SMTV がおすすめのモデルとそのサイズを表示します。上の表のモデルの横にある **Download**（ダウンロード）を押して待ちます（5〜10 GB）。
4. 完了。SMTV がそのモデルを各ステップに自動で割り当てます。

SMTV はリクエストごとに、配信のテキスト全体が収まるよう Ollama のメモリを設定します。Ollama の設定を変える必要はありません。

## 2b. LM Studio

1. [lmstudio.ai/download](https://lmstudio.ai/download) から LM Studio をダウンロードしてインストールします。
2. LM Studio で **Discover** を開き、**Qwen3 8B**（表に合わせて 14B でも）を検索して **Download** を押します。
3. **Developer** タブを開き、**Start server** をオンにします（ポート 1234 で待ち受けます）。そこでモデルを読み込みます。
4. SMTV で：**Settings → AI → Free, on this computer → Find on this computer**。SMTV が LM Studio を見つけます。

## 3. クリップを作る

SMTV に[動画ファイル](first-clip.md)を渡します。無料 AI を使う場合でも、Twitch や YouTube のリンクには[アカウント](account.md)が必要です：
録画を取得するのはアカウントだからです。

無料 AI はクラウドのものより遅く、長い配信では数時間かかることもあります。パソコンはつけたままにしておいてください。
