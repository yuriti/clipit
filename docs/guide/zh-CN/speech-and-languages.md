<!-- languages -->
[Русский](../speech-and-languages.md) · [English](../en/speech-and-languages.md) · [Қазақша](../kk/speech-and-languages.md) · [Oʻzbekcha](../uz/speech-and-languages.md) · [Azərbaycanca](../az/speech-and-languages.md) · [Кыргызча](../ky/speech-and-languages.md) · **简体中文** · [日本語](../ja/speech-and-languages.md) · [한국어](../ko/speech-and-languages.md) · [Tiếng Việt](../vi/speech-and-languages.md) · [Bahasa Indonesia](../id/speech-and-languages.md) · [हिन्दी](../hi/speech-and-languages.md) · [বাংলা](../bn/speech-and-languages.md) · [Español](../es/speech-and-languages.md) · [Português](../pt-BR/speech-and-languages.md) · [Deutsch](../de/speech-and-languages.md)

> 🌐 本页面由机器自动翻译。欢迎帮助改进：[Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [原文: Русский](../speech-and-languages.md)。

# 语音与语言

SMTV 首先把直播的语音转成文字，并记下每个词的时间——AI 正是靠这个来理解发生了什么。这一步**在你的电脑上免费完成**。
SMTV 会自己识别直播的语言。

| 语言 | 模型 | 下载（一次） | 在 12 核处理器上的速度 |
|---|---|---|---|
| 俄语 | GigaAM-v3，专为俄语打造 | 0.9 GB | 比实时快 54 倍 |
| 25 种欧洲语言：英语、西班牙语、德语、法语、意大利语、葡萄牙语、波兰语、乌克兰语等 | Parakeet-TDT v3 | 2.4 GB | 比实时快 33 倍 |
| 其他所有语言：中文、日语、韩语、印地语、孟加拉语、哈萨克语、乌兹别克语、阿塞拜疆语、越南语、印尼语以及其他几十种 | Whisper large-v3-turbo | 1.6 GB | 尚未测量 |

第一次遇到某种语言的直播时，对应的模型会自动下载。不需要显卡；NVIDIA 显卡能让它更快。在 Mac 上，Whisper 在处理器上运行，会慢一些。

**Settings → Speech to text**（设置 → 语音转文字）显示所有模型：在哪里运行、支持哪些语言、大小和速度，并有 **Download**（下载）和
**Remove**（删除）按钮。在那里，每种语言都可以换用别的模型，也可以用你自己的密钥（Groq 或 OpenAI）使用 **Whisper in the cloud**（云端 Whisper）——
在性能弱的电脑上更快，但这样声音就会离开你的电脑。

<img src="../../images/speech.png" alt="Settings → Speech to text：模型以及它们负责的语言" width="820">

**窗口的语言**是另一回事：SMTV 使用你电脑的语言；在 **Settings → Language and theme**（设置 → 语言和主题）里可以选别的。
你的语言没有或只翻译了一半？[帮忙翻译](../../translations.md)——不需要会编程。
