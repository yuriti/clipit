<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · **简体中文** · [日本語](../ja/install.md) · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 本页面由机器自动翻译。欢迎帮助改进：[Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls) · [原文: Русский](../install.md)。

# 安装 SMTV

下载一个文件，打开它，就会出现 **SMTV** 图标。SMTV 需要的一切都在里面。不需要管理员密码。

| 你的电脑 | 下载 | 大小 |
|---|---|---|
| **Windows 10 或 11**（64 位） | [Windows 版 SMTV](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows-setup.exe) | 约 130 MB |
| **Mac** — Apple 芯片（M1 及更新）或 Intel，macOS 13+ | [Mac 版 SMTV](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | 约 270 MB |

所有版本及其校验和：[发布页面](https://github.com/yuriti/clipit/releases/latest)。

**为什么第一次打开时系统会发出警告。** SMTV 还没有数字签名。Windows 的签名稍晚一些就会有，macOS 的签名会尽快有，
之后这个警告就会消失。SMTV 的代码是公开的：任何人都可以读一读它在做什么。

## Windows

1. 下载 **Windows 版 SMTV**（文件 `SMTV-…-windows-x64-setup.exe`）并打开它。
2. Windows 会弹出一个蓝色窗口 **“Windows 已保护你的电脑”**（Windows protected your PC）。点 **更多信息**（More info），
   再点 **仍要运行**（Run anyway）。
3. 安装程序会问几个问题（语言、要不要在桌面放图标）——点 **Next**（下一步）和 **Install**（安装）。
4. 最后保持 **Launch SMTV**（启动 SMTV）勾选，点 **Finish**（完成）。下次从 **开始** 菜单（或桌面图标）启动 SMTV。

安装程序会把 SMTV 装在你自己的用户文件夹里；它会出现在 **设置 → 应用**（Settings → Apps）里，可以在那里卸载。

**不安装也能用：** 下载 [ZIP 压缩包](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip)，
解压到任意位置（比如“文档”文件夹），打开 `SMTV` 文件夹里的 **SMTV.exe**。这个版本不会自己更新：新版本就是新的 ZIP。

### Windows 11：智能应用控制

如果开启了 **智能应用控制**（Smart App Control，在 Windows 安全中心 → 应用和浏览器控制 里），Windows 会完全阻止没有签名的
程序，而且没有放行的按钮。为了 SMTV，你不需要关闭智能应用控制。改用一行命令安装 SMTV 即可——开着智能应用控制也能用：
[在终端里用一行命令](#给有经验的用户在终端里用一行命令)。等 SMTV 有了签名，下载版在那里也能用。

## Mac

1. 下载 **Mac 版 SMTV**。它是适用于所有 Mac 的同一个文件，无论是 Apple 芯片还是 Intel：SMTV 会自动启动为你的 Mac 处理器制作的版本。
2. 打开下载好的 `.dmg`。会出现一个窗口，里面有 SMTV 和 **应用程序**（Applications）文件夹：把 **SMTV** 拖到
   **应用程序** 上。
3. 打开 **应用程序**，双击 **SMTV**。macOS 会说它无法检查 SMTV，并且不会打开它。点 **完成**（Done）。
4. 打开 **系统设置 → 隐私与安全性**（System Settings → Privacy & Security），向下滚动。在“已阻止 SMTV……”旁边点
   **仍要打开**（Open Anyway），输入你的 Mac 密码，再点 **打开**（Open）。
   在 macOS 14 上有更快的办法：在“应用程序”里右键点 **SMTV** → **打开** → **打开**。

只有第一次需要这样：之后 SMTV 像平常一样单击就能打开，从“应用程序”或启动台（Launchpad）都可以。同样的步骤也写在 `.dmg`
里的“How to open”文件中。

## 第一次启动

SMTV 会检查你的电脑，并显示做出第一个切片的三个步骤。在它们下面，它会提供 **你的语言的语音识别**——把直播里的话变成
文字的部分。它不在下载包里，因为每种语言都需要自己的那一份（0.9–2.5 GB）。点 **Fix**（修复）并看着进度条，或者先跳过：
第一个任务会自己把它下载下来。

**你需要：** 至少 5 GB 可用空间，6 小时的直播需要 20 GB；网络连接。不需要显卡。

## 给有经验的用户：在终端里用一行命令

同一个 SMTV，用 [uv](https://astral.sh/uv)——一个用来安装 Python 程序的官方小工具——装进你的用户文件夹。在 **Linux** 上、
开着 **智能应用控制** 时，或者你更喜欢终端时，可以用这种方式。它和下载版一样从窗口里更新。

**Windows：** 点击 **开始**，输入 `PowerShell`，打开 **Windows PowerShell**（蓝色窗口），粘贴这行（右键单击或 Ctrl+V），
然后按 **Enter**：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

开着智能应用控制时，安装程序会把 SMTV 装在来自 python.org 的已签名 Python 上（可能会要求安装 Python——同意即可），
并通过它启动 SMTV。如果终端提示无法运行 `smtv`，请改用 **SMTV** 图标。

**Mac 或 Linux：** 打开 **Terminal**（终端；在 Mac 上：按 Cmd+Space，输入 `Terminal`，按 Enter），粘贴这行，然后按 **Enter**：

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

等到它显示完成（2–10 分钟）。SMTV 会自己打开；**SMTV** 图标在 Windows 的“开始”菜单里，Mac 的“应用程序”里，
Linux 的应用程序菜单里。用这种方式安装时，SMTV 第一次会提供用 **Fix**（修复）安装 **ffmpeg**（视频工具）；
上面的下载版里已经带了它。

两个安装程序都很短，而且是公开的：[install.ps1](../../../install/install.ps1)、[install.sh](../../../install/install.sh)。

## 如果系统发出警告

- **Windows：“Windows 已保护你的电脑”**（Windows protected your PC，SmartScreen）。点 **更多信息**（More info），
  再点 **仍要运行**（Run anyway）。
- **Windows 11：智能应用控制（Smart App Control）阻止了 SMTV。** 在 SMTV 有签名之前，请用
  [在终端里用一行命令](#给有经验的用户在终端里用一行命令)。
- **Windows：防火墙询问** SMTV 是否可以使用网络。为 **专用** 网络允许它：SMTV 需要网络才能在你的手机上打开。
  如果你不需要用手机，拒绝也没关系。
- **Mac：«SMTV cannot be opened»**（无法打开“SMTV”）、“Apple 无法验证……”或“无法验证开发者”。打开 **系统设置 →
  隐私与安全性**（System Settings → Privacy & Security），向下滚动，点 SMTV 旁边的 **仍要打开**（Open Anyway）。
- **Mac：«SMTV would like to accept incoming connections»**（“SMTV”想要接受传入的网络连接）——如果你想在手机上用 SMTV，就允许它。
- **杀毒软件** 报警？SMTV 是新程序，还没有签名，所以有些杀毒软件会对它比较谨慎。它的代码是公开的，每个文件的校验和都在
  [发布页面](https://github.com/yuriti/clipit/releases/latest)上（`SHA256SUMS.txt`）。

下一步：[你的第一个切片](first-clip.md)。
