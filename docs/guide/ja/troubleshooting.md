<!-- languages -->
[English](../troubleshooting.md) · [Русский](../ru/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · **日本語** · [한국어](../ko/troubleshooting.md) · [Tiếng Việt](../vi/troubleshooting.md) · [Bahasa Indonesia](../id/troubleshooting.md) · [हिन्दी](../hi/troubleshooting.md) · [বাংলা](../bn/troubleshooting.md) · [Español](../es/troubleshooting.md) · [Português](../pt-BR/troubleshooting.md) · [Deutsch](../de/troubleshooting.md)

> 🌐 このページは自動翻訳されています。改善にご協力ください：[Weblate](https://hosted.weblate.org/engage/smtv/) · [プルリクエスト](https://github.com/streammomenttv/smtv/pulls)。

# うまくいかないとき

## 1. Computer check → Fix（パソコンのチェック → 修正）

**Settings → Computer check**（設定 → パソコンのチェック）は SMTV に必要なものをすべて調べ、何が問題なくて何が問題かを一行ずつ教えてくれます。
問題の横には **Fix** ボタンがあります：SMTV が自分でできるものをインストールしたり修復したりし、何をしているかを表示します。

<img src="../../images/check.png" alt="Settings → Computer check：各行の状態と Fix ボタン" width="820">

| 行の表示 | どうするか |
|---|---|
| **Video (ffmpeg)** がない | **Fix** を押す：SMTV が使っている動画ツール ffmpeg をインストールします。 |
| **Captions**（字幕）が動かない | **Fix** を押す：SMTV が字幕を描画できる ffmpeg をインストールします。 |
| **AI**：何もつながっていない | **Settings → AI** でひとつ選ぶ——[どれにするか](connect-ai.md)。 |
| **Connection to StreamMoment**（StreamMoment への接続）に失敗 | インターネットを確認。VPN やファイアウォールがブロックしているかもしれません。それがなくてもファイルは使えます。 |
| **Free space**（空き容量）が少ない | ディスクを空ける：6 時間の配信は処理中に約 20 GB 必要です。 |
| **Speech to text**：モデルがダウンロードされていない | 最初のリクエストで自動でダウンロードされます。または **Settings → Speech to text** で **Download** を押します。 |

管理者パスワードが必要な修正が黙って実行されることはありません：SMTV はコマンド入りのターミナルを開くので、何をするかを確認できます。

## 2. よくある問題

- **リンクが使えない。** リンクには [StreamMoment アカウント](account.md)が必要です。アカウントがない？録画を自分でダウンロードして、
  ファイルを SMTV に渡してください。
- **クリップがない、またはとても少ない。** SMTV は AI が良いと評価した場面だけを残します。短い配信や静かな配信では少なくなることがあります。
  パソコン上の無料 AI は、クラウドのものより見つかる良い場面が少なくなります。
- **「リクエストが多すぎます」（«Too many requests»）。** AI サービスの無料プランが上限に達しました：待つか、有料プランかアカウントを使ってください。
- **スマホで SMTV が開かない。** 同じ Wi-Fi、VPN なし、ファイアウォールで SMTV を許可——[スマホ](phone.md)を見てください。
- **Windows：ターミナルが `smtv` を拒否する。** それはスマート アプリ コントロールです。アイコンから SMTV を起動してください。
- **ウィンドウと SMTV の接続が切れた。** ウィンドウを閉じて、SMTV をもう一度開いてください。

止まったリクエストは続けられます：**Continue**（続行）を押すと、SMTV は同じステップから再開し、終わった作業はやり直しません。

## 3. 問題を報告する

それでもだめ？教えてください——みんなの役に立ちます。

1. **Settings → Computer check → Report a problem**（設定 → パソコンのチェック → 問題を報告）（**Report…** ボタン。**Settings → About** にもあります）、
   または失敗したリクエストの下にあるボタン。
2. SMTV がレポートに入る内容を表示します：バージョン、パソコンのチェック結果、設定、ログ。**キーとトークンは取り除かれ**、
   ホームフォルダは `~` と表示されます。リンクとファイル名は、チェックを入れない限り含まれません。
3. **Save and open GitHub**（保存して GitHub を開く）を押します。SMTV がアーカイブを保存し、概要が記入された新しい issue がブラウザで開きます。
   アーカイブをそこにドラッグして **Submit** を押します。

SMTV が自分で何かを送ることはありません。ウィンドウを使わない場合：ターミナルで `smtv report` を実行します。
[issue を直接作成](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml)することもできます。
