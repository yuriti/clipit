<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · **日本語** · [한국어](../ko/install.md) · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 このページは自動翻訳されています。改善にご協力ください：[Weblate](https://hosted.weblate.org/engage/smtv/) · [プルリクエスト](https://github.com/yuriti/clipit/pulls) · [原文: Русский](../install.md)。

# SMTV をインストール

ファイルを 1 つダウンロードして開けば、**SMTV** のアイコンが現れます。SMTV に必要なものはすべて入っています。
管理者パスワードは不要です。

| あなたのパソコン | ダウンロード | サイズ |
|---|---|---|
| **Windows 10 または 11**（64 ビット） | [Windows 版 SMTV](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows-setup.exe) | 約 130 MB |
| **Mac** — Apple シリコン（M1 以降）または Intel、macOS 13+ | [Mac 版 SMTV](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | 約 270 MB |

すべてのバージョンとチェックサム：[リリースページ](https://github.com/yuriti/clipit/releases/latest)。

**初回にシステムが警告するわけ。** SMTV にはまだデジタル署名がありません。Windows 用の署名はもう少し後に、macOS 用の署名は
できるだけ早く付き、そうすればこの警告は出なくなります。SMTV のコードは公開されています：何をしているかは誰でも読めます。

## Windows

1. **Windows 版 SMTV**（ファイル `SMTV-…-windows-x64-setup.exe`）をダウンロードして開きます。
2. Windows に青いウィンドウ **「Windows によって PC が保護されました」**（Windows protected your PC）が出ます。
   **詳細情報**（More info）を押し、続けて **実行**（Run anyway）を押します。
3. インストーラーがいくつか質問します（言語、デスクトップのアイコン）——**Next**（次へ）と **Install**（インストール）を押します。
4. 最後に **Launch SMTV**（SMTV を起動）にチェックを入れたまま **Finish**（完了）を押します。次回からは **スタート**
   メニュー（またはデスクトップのアイコン）から SMTV を起動します。

インストーラーは SMTV をあなた自身のユーザーフォルダに入れます。SMTV は **設定 → アプリ**（Settings → Apps）に表示され、
そこから削除できます。

**インストールせずに使う：** [ZIP ファイル](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip)
をダウンロードし、好きな場所（たとえばドキュメント）に展開して、`SMTV` フォルダの **SMTV.exe** を開きます。
このコピーは自動でアップデートされません：新しいバージョンは新しい ZIP です。

### Windows 11：スマート アプリ コントロール

**スマート アプリ コントロール**（Smart App Control。Windows セキュリティ → アプリとブラウザーの制御）が有効だと、Windows は
署名のないプログラムを完全にブロックし、通すためのボタンもありません。SMTV のためにスマート アプリ コントロールをオフにする
必要はありません。代わりに 1 行で SMTV をインストールしてください——スマート アプリ コントロールが有効でも動きます：
[ターミナルで 1 行](#経験者向けターミナルで-1-行)。SMTV に署名が付けば、ダウンロード版もそこで動くようになります。

## Mac

1. **Mac 版 SMTV** をダウンロードします。Apple シリコンでも Intel でも、どの Mac でも同じ 1 つのファイルです。SMTV が Mac のプロセッサ用に作られた版を自動で起動します。
2. ダウンロードした `.dmg` を開きます。SMTV と **アプリケーション**（Applications）フォルダのあるウィンドウが開くので、
   **SMTV** を **アプリケーション** にドラッグします。
3. **アプリケーション** を開いて **SMTV** をダブルクリックします。macOS は SMTV を確認できないと言って開きません。
   **完了**（Done）を押します。
4. **システム設定 → プライバシーとセキュリティ**（System Settings → Privacy & Security）を開いて下にスクロールします。
   「SMTV はブロックされました…」の横の **このまま開く**（Open Anyway）を押し、Mac のパスワードを入力して **開く**（Open）を押します。
   macOS 14 ならもっと短い方法があります：アプリケーションで **SMTV** を右クリック → **開く** → **開く**。

これは初回だけです：その後はアプリケーションや Launchpad から普通にクリックすれば SMTV が開きます。同じ手順は `.dmg` の中の
ファイル「How to open」にも書いてあります。

## 初めての起動

SMTV はパソコンをチェックし、最初のクリップまでの 3 つのステップを表示します。その下で **あなたの言語の音声認識** ——
配信の話し声を文字にする部分——を提案します。これはダウンロードには入っていません。言語ごとに別のもの（0.9〜2.5 GB）が
必要だからです。**Fix**（修正）を押して進み具合を見るか、飛ばしてもかまいません：最初のリクエストが自動でダウンロードします。

**必要なもの：** 空き容量が最低 5 GB、6 時間の配信なら 20 GB。インターネット接続。グラフィックボードは不要です。

## 経験者向け：ターミナルで 1 行

同じ SMTV を、[uv](https://astral.sh/uv)——Python のプログラムをインストールするための小さな公式ツール——で
あなたのユーザーフォルダにインストールします。**Linux** のとき、**スマート アプリ コントロール** が有効なとき、
またはターミナルのほうが好きなときに使ってください。ダウンロード版と同じようにウィンドウからアップデートできます。

**Windows：** **スタート**を押して `PowerShell` と入力し、**Windows PowerShell**（青いウィンドウ）を開いて、この行を貼り付け
（右クリックか Ctrl+V）、**Enter** を押します：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

スマート アプリ コントロールが有効な場合、インストーラーは python.org の署名付き Python の上に SMTV をインストールし
（Python のインストールを求められたら同意してください）、それを通して SMTV を起動します。ターミナルで `smtv` を実行できないと
言われたら、代わりに **SMTV** アイコンを使ってください。

**Mac または Linux：** **ターミナル**（Terminal）を開き（Mac なら Cmd+Space を押して `Terminal` と入力し、Enter）、
この行を貼り付けて **Enter** を押します：

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

完了と表示されるまで待ちます（2〜10 分）。SMTV が自動で開きます。**SMTV** のアイコンは、Windows ではスタートメニューに、
Mac ではアプリケーションに、Linux ではアプリケーションメニューにあります。この方法では、SMTV は初回に **ffmpeg**（動画ツール）
を **Fix**（修正）でインストールするよう提案します。上のダウンロード版には最初から入っています。

インストーラーはどちらも短く、公開されています：[install.ps1](../../../install/install.ps1)、[install.sh](../../../install/install.sh)。

## システムに警告されたら

- **Windows：「Windows によって PC が保護されました」**（Windows protected your PC、SmartScreen）。**詳細情報**（More info）を押し、
  続けて **実行**（Run anyway）を押します。
- **Windows 11：スマート アプリ コントロール（Smart App Control）が SMTV をブロックする。** SMTV に署名が付くまでは
  [ターミナルで 1 行](#経験者向けターミナルで-1-行)を使ってください。
- **Windows：ファイアウォールが**、SMTV にネットワークの使用を許可するか尋ねてきます。**プライベート**ネットワークで許可してください：
  スマホで SMTV を開くのに必要です。スマホを使わないなら、拒否してもかまいません。
- **Mac：«SMTV cannot be opened»**（「SMTV」を開けません）、「Apple は…を検証できませんでした」や「開発元を検証できません」。
  **システム設定 → プライバシーとセキュリティ**（System Settings → Privacy & Security）を開いて下にスクロールし、SMTV の横の
  **このまま開く**（Open Anyway）を押します。
- **Mac：«SMTV would like to accept incoming connections»**（「SMTV」へのネットワーク受信接続を許可しますか？）——スマホで SMTV を
  使いたいなら許可してください。
- **ウイルス対策ソフト**が反応した？SMTV は新しく、まだ署名がないので、慎重に扱うウイルス対策ソフトもあります。コードは公開されていて、
  すべてのファイルのチェックサムは[リリースページ](https://github.com/yuriti/clipit/releases/latest)にあります
  （`SHA256SUMS.txt`）。

次へ：[最初のクリップ](first-clip.md)。
