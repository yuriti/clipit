<!-- languages -->
[Русский](../update-and-remove.md) · [English](../en/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · **日本語** · [한국어](../ko/update-and-remove.md) · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 このページは自動翻訳されています。改善にご協力ください：[Weblate](https://hosted.weblate.org/engage/smtv/) · [プルリクエスト](https://github.com/yuriti/clipit/pulls) · [原文: Русский](../update-and-remove.md)。

# アップデートと削除

## アップデート

SMTV は 1 日に 1 回、新しいバージョンを確認します（オフにもできます）。新しいバージョンがあると **Version … is available**
（バージョン … が利用可能です）と表示されるので、**Update**（アップデート）を押します。

- SMTV が閉じ、アップデートされ、自動でまた開きます。たいてい 1 分以内です。
- リクエストの実行中なら、アップデートは終わるまで待ちます——または **Stop the jobs and update**（ジョブを止めてアップデート）を押します。
  そのあと **Continue** で、同じステップからジョブを再開できます。
- 新しいバージョンが起動しなかった場合は、前のバージョンが自動で戻ります。
- 新しいバージョンには SMTV の作者が署名しています。SMTV はインストール前に署名を確認します。

アップデートについてはすべて **Settings → Computer check → Updates**（設定 → パソコンのチェック → アップデート）にあります。

Windows 版や Mac 版の SMTV をダウンロードしましたか？**Update**（アップデート）を押すと新しいインストーラーがダウンロードされ、
確認されてから開きます：そこでインストールを最後まで進めてください（Mac では新しい SMTV をアプリケーションにドラッグし、
**置き換える**（Replace）を押します）。ZIP 版の Windows のコピーは自動でアップデートされません：
[リリースページ](https://github.com/yuriti/clipit/releases/latest)から新しい ZIP をダウンロードしてください。

別の方法で SMTV をインストールしましたか？Docker では、新しいバージョンは新しいイメージです。[上級者向け](../../advanced.md#docker)を見てください。

## 削除

**Settings → Computer check → Remove SMTV from this computer**（このパソコンから SMTV を削除）（**Remove…** ボタン）で、プログラムと SMTV のアイコンが削除されます。
クリップは残ります——それも削除するなら **Also remove clips, jobs, settings and keys**（クリップ、ジョブ、設定、キーも削除）にチェックを入れてください。

Windows 版や Mac 版の SMTV をダウンロードしましたか？プログラム本体はシステムのやり方で削除してください（上のボタンが削除するのは、
チェックを入れた場合のクリップと設定だけです）：

- **Windows：** **設定 → アプリ → インストールされているアプリ → SMTV → アンインストール**
  （Settings → Apps → Installed apps → SMTV → Uninstall）。ZIP 版のコピーは、そのフォルダを削除します。
- **Mac：** **SMTV** を **アプリケーション**（Applications）から **ゴミ箱**（Trash）にドラッグします。

ターミナルで 1 行でインストールしましたか？ウィンドウを使わずに、ターミナルで：

```bash
smtv uninstall
```

`--data` を付けると、クリップと設定も削除されます。自分でインストールしたプログラム（Ollama、LM Studio）は残ります：
ほかのプログラムと同じように削除してください。
