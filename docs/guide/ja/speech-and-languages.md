<!-- languages -->
[English](../speech-and-languages.md) · [Русский](../ru/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · [简体中文](../zh-CN/speech-and-languages.md) · **日本語** · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 このページは自動翻訳されています。改善にご協力ください：[Weblate](https://hosted.weblate.org/engage/smtv/) · [プルリクエスト](https://github.com/streammomenttv/smtv/pulls)。

# 音声と言語

SMTV はまず配信の音声を、すべての単語の時刻付きで文字に起こします——そうやって AI は何が起きたかを理解します。
これは**あなたのパソコンで、無料で**行われます。配信の言語は SMTV が自動で判別します。

| 言語 | モデル | ダウンロード（一度だけ） | 12 コアのプロセッサでの速度 |
|---|---|---|---|
| ロシア語 | GigaAM-v3、ロシア語専用 | 0.9 GB | 実時間の 54 倍速 |
| ヨーロッパの 25 言語：英語、スペイン語、ドイツ語、フランス語、イタリア語、ポルトガル語、ポーランド語、ウクライナ語など | Parakeet-TDT v3 | 2.4 GB | 実時間の 33 倍速 |
| そのほかのすべての言語：中国語、日本語、韓国語、ヒンディー語、ベンガル語、カザフ語、ウズベク語、アゼルバイジャン語、ベトナム語、インドネシア語、ほか数十 | Whisper large-v3-turbo | 1.6 GB | まだ計測していません |

モデルは、その言語の配信が初めて来たときに自動でダウンロードされます。グラフィックボードは不要ですが、NVIDIA のボードがあれば速くなります。
Mac では Whisper はプロセッサで動くため、遅くなります。

**Settings → Speech to text**（設定 → 文字起こし）には、すべてのモデルが表示されます：どこで動くか、対応言語、サイズ、速度、そして
**Download**（ダウンロード）と **Remove**（削除）。そこで言語ごとに別のモデルを選ぶこともでき、自分のキー（Groq または OpenAI）で
**Whisper in the cloud**（クラウドの Whisper）を使うこともできます——非力なパソコンでは速くなりますが、その場合は音声がパソコンの外に出ます。

<img src="../../images/speech.png" alt="Settings → Speech to text：モデルと、それぞれが担当する言語" width="820">

**ウィンドウの言語**は別です：SMTV はあなたのパソコンの言語で表示され、**Settings → Language and theme**（設定 → 言語とテーマ）で
別の言語を選べます。あなたの言語がない、または半分しか翻訳されていない？[翻訳に協力してください](../../translations.md)——プログラミングは不要です。
