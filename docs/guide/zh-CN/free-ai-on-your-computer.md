<!-- languages -->
[English](../free-ai-on-your-computer.md) · [Русский](../ru/free-ai-on-your-computer.md) · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · **简体中文** · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 本页面由机器自动翻译。欢迎帮助改进：[Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls)。

# 你电脑上的免费 AI

AI 可以直接在你的电脑上免费运行：什么都不会离开电脑，也不用付任何钱。你需要一个运行 AI 模型的程序——
**Ollama** 或 **LM Studio**——以及一个模型，比如 **Qwen**。SMTV 会自己找到这个程序。

**说实话：** 能在家用电脑上运行的模型比云端模型弱，所以切片效果会差一些，而且推荐的模型都还没有和 SMTV 一起测试过。
如果结果让你失望，可以试试[账户](account.md)或[密钥](get-a-key.md)。

## 1. 哪个模型适合你的电脑

关键是显卡的**显存**（在 Apple 芯片的 Mac 上：看全部内存）。

| 显存 | 模型 | 下载大小 | 说明 |
|---|---|---|---|
| 少于 8 GB | — | — | 太少了：请用账户或密钥 |
| 8 GB | `qwen3:8b` | 5.2 GB | 能用得还不错的最轻量模型 |
| 10–12 GB | `qwen3-vl:8b` 或 `gemma3:12b` | 6.1 / 8.1 GB | 这两个还会看视频画面 |
| 16 GB 及以上 | `qwen3:14b` | 9.3 GB | 四个里最好的 |

不推荐小于 7B（“70 亿”参数）的模型：它们会把 SMTV 需要的回答弄乱。

**怎么查看显存：**
- **Windows：** 按 Ctrl+Shift+Esc →“性能”（**Performance**）→ **GPU** →“专用 GPU 内存”（**Dedicated GPU memory**）。
- **Mac：** 苹果菜单 →“关于本机”（**About This Mac**）→“内存”（**Memory**）。Mac 的内存和 AI 共用：16 GB 选 `qwen3:8b`，
  32 GB 或更多选 `qwen3:14b`。

## 2a. Ollama（最简单）

1. 从 [ollama.com/download](https://ollama.com/download) 下载 Ollama，像安装其他程序一样安装。它会自己启动，
   图标在时钟旁边。
2. 在 SMTV 中：**Settings → AI → Free, on this computer → Find on this computer**（设置 → AI → 免费，在这台电脑上 → 在这台电脑上查找）。SMTV 会找到 Ollama。
3. 在列表中打开 **Ollama**：SMTV 会显示推荐的模型及其大小。在上表中对应的模型旁点 **Download**（下载），然后等待（5–10 GB）。
4. 完成。SMTV 会自己为各个步骤选用这个模型。

SMTV 会为每个任务设置 Ollama 的内存，确保整场直播的文字都能放得下；你不需要修改 Ollama 的设置。

## 2b. LM Studio

1. 从 [lmstudio.ai/download](https://lmstudio.ai/download) 下载 LM Studio 并安装。
2. 在 LM Studio 中打开 **Discover**，搜索 **Qwen3 8B**（或按上表选 14B），点 **Download**。
3. 打开 **Developer** 标签页，开启 **Start server**（它监听 1234 端口）。在那里加载模型。
4. 在 SMTV 中：**Settings → AI → Free, on this computer → Find on this computer**。SMTV 会找到 LM Studio。

## 3. 做一个切片

给 SMTV 一个[视频文件](first-clip.md)。即使用免费 AI，Twitch 或 YouTube 链接也需要[账户](account.md)：录像是由账户获取的。

免费 AI 比云端的慢；一场长直播可能需要几个小时。请让电脑保持开机。
