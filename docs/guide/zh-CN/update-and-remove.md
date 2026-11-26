<!-- languages -->
[Русский](../update-and-remove.md) · [English](../en/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · **简体中文** · [日本語](../ja/update-and-remove.md) · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 本页面由机器自动翻译。欢迎帮助改进：[Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/streammomenttv/smtv/pulls) · [原文: Русский](../update-and-remove.md)。

# 更新和卸载

## 更新

SMTV 每天检查一次新版本（可以关闭）。有新版本时，它会显示 **Version … is available**（版本 … 可用）：点 **Update**（更新）。

- SMTV 会关闭、更新，然后自己重新打开，通常不到一分钟。
- 如果有任务正在运行，更新会等到任务结束——或者点 **Stop the jobs and update**（停止任务并更新）；之后 **Continue** 会从同一步继续这些任务。
- 如果新版本启动不了，会自动恢复到上一个版本。
- 新版本由 SMTV 的作者签名；SMTV 在安装前会检查签名。

关于更新的一切都在 **Settings → Computer check → Updates**（设置 → 电脑检查 → 更新）里。

下载的是 Windows 版或 Mac 版 SMTV？**Update**（更新）会下载新的安装程序，检查它并打开它：在那里完成安装（在 Mac 上，
把新的 SMTV 拖到“应用程序”上，再点 **替换**（Replace））。ZIP 里的 Windows 版不会自己更新：请从
[发布页面](https://github.com/streammomenttv/smtv/releases/latest)下载新的 ZIP。

用别的方式安装的 SMTV？在 Docker 中，新版本就是新镜像；见[给高级用户](../../advanced.md#docker)。

## 卸载

**Settings → Computer check → Remove SMTV from this computer**（从这台电脑上删除 SMTV）（**Remove…** 按钮）会删除程序和 SMTV 图标。你的切片会保留——勾选
**Also remove clips, jobs, settings and keys**（同时删除切片、任务、设置和密钥）可以把它们也删掉。

下载的是 Windows 版或 Mac 版 SMTV？请用系统自己的方式卸载程序本身（上面的按钮只会删除切片和设置，而且要你勾选了才删）：

- **Windows：** **设置 → 应用 → 已安装的应用 → SMTV → 卸载**（Settings → Apps → Installed apps → SMTV → Uninstall）。
  ZIP 里的版本：直接删除它的文件夹。
- **Mac：** 把 **SMTV** 从 **应用程序**（Applications）拖到 **废纸篓**（Trash）。

用一行命令在终端里安装的？不用窗口，在终端里：

```bash
smtv uninstall
```

加上 `--data` 可以同时删除切片和设置。你自己安装的程序（Ollama、LM Studio）会保留：像卸载其他程序一样卸载它们。
