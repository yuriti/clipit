<!-- Translations: README.<language>.md, the same structure. A change here changes README.ru.md in the same PR;
     the other languages follow (each says it was translated automatically and links Weblate). Pictures: docs/images/. -->
<div align="center">

# SMTV

**長い配信を、短いクリップとまとめ動画に。無料で、あなたのパソコンの中で。**

<!-- languages -->
[English](README.md) · [Русский](README.ru.md) · [Қазақша](README.kk.md) · [Oʻzbekcha](README.uz.md) · [Azərbaycanca](README.az.md) · [Кыргызча](README.ky.md) · [简体中文](README.zh-CN.md) · **日本語** · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [हिन्दी](README.hi.md) · [বাংলা](README.bn.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [Deutsch](README.de.md)

> 🌐 このページは自動翻訳されています。改善にご協力ください：[Weblate](https://hosted.weblate.org/engage/smtv/) · [プルリクエスト](https://github.com/streammomenttv/smtv/pulls)。

[![最新リリース](https://img.shields.io/github/v/release/streammomenttv/smtv?label=release)](https://github.com/streammomenttv/smtv/releases/latest)
[![ダウンロード数](https://img.shields.io/pepy/dt/smtv?label=downloads)](https://pepy.tech/projects/smtv)
[![スター](https://img.shields.io/github/stars/streammomenttv/smtv?style=flat)](https://github.com/streammomenttv/smtv/stargazers)
[![ライセンス：MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/smtv)](https://pypi.org/project/smtv/)
[![Weblate で翻訳](https://hosted.weblate.org/widget/smtv/svg-badge.svg)](https://hosted.weblate.org/engage/smtv/)

<img src="docs/images/demo.gif" alt="SMTV：配信の録画を入れると、SMTV が見どころを見つけ、縦型クリップを一本ずつ作ります" width="820">

[**SMTV をダウンロード**](#ダウンロード) · [ステップごとのガイド](docs/guide/ja/README.md) · [他のツールとの比較](#smtv-と他のツールの比較) · [よくある質問](#よくある質問)

</div>

---

6 時間配信しました。その中には投稿したくなる場面が 10 個ほど眠っています。でも、それを見つけるにはもう一度全部見直さなければなりません。
**SMTV が代わりに見てくれます。** Twitch や YouTube の録画リンクを貼るか、動画ファイルを選ぶだけ。SMTV は配信を最初から最後まで聞いて、
いちばんの見どころを選び、TikTok・Shorts・Reels 向けの**そのまま投稿できる縦型クリップ**を作ります。字幕付きで、Web カメラの映像は上に配置。
さらに、配信全体の **20〜30 分のまとめ動画**も YouTube 向けに作ります。

## できること

| | |
|---|---|
| 🎬 **すぐ投稿できるクリップ** | 縦型 9:16、大きな字幕、冒頭に短いタイトルカード、ゲーム画面の上に配信者の Web カメラ。 |
| ⏱️ **長い配信も大丈夫** | 6〜12 時間の録画から最大 30 本のクリップ。クリップは一本ずつ出てくるので、全部できあがる前から投稿を始められます。 |
| 📺 **配信全体のまとめ動画** | YouTube 向けの 20〜30 分の動画。配信そのものから、見る価値のある部分だけを残したものです。 |
| 🗣️ **多くの言語に対応** | ロシア語、ヨーロッパの 25 言語、ほか数十の言語。SMTV は音声をあなたのパソコン上で文字に起こします。 |
| 🔒 **ファイルは手元に** | クリップはあなたのパソコンで作られ、保存されます。どこかのサイトにアップロードされることはありません。 |
| 💸 **無料でオープン** | MIT ライセンス：自由に使って、共有して、クライアントの仕事にも使えます。透かしなし、時間の制限なし。 |

## 動いているところを見る

**リンクを貼るかファイルを選ぶだけ。あとは各ステップを見守るだけです。** すべてのステップが画面に表示されます：音声の文字起こし、
見どころ探し、その評価、各クリップの編集。

<img src="docs/images/new-request.gif" alt="新しいリクエスト：動画ファイルを選ぶと SMTV が動き出し、各ステップを表示します" width="820">

**クリップは一本ずつ出てきます。** SMTV の中でそのまま見て、ダウンロードして、投稿できます。

<img src="docs/images/clips.png" alt="配信から完成したクリップがグリッドに並んでいる様子" width="820">

**どのクリップにもテキストが付いています。** 何が話されたのか、SMTV がなぜその場面を選んだのかが読めます。

<img src="docs/images/viewer.png" alt="文字起こしの横で再生されているクリップ" width="820">

**そして配信全体のまとめ動画**を YouTube 向けに。クリップのあとに作られます。

<img src="docs/images/recap.png" alt="SMTV に表示された配信のまとめ動画" width="820">

**ライトかダーク**か——パソコンの設定に合わせます。

<img src="docs/images/dark.png" alt="ダークテーマの SMTV" width="820">

<sub>これらの画像の配信はデモ用に作ったものです：小さなゲーム、Web カメラの代わりのアニメのマスコット、そして合成音声。
実在の人物は映っていません。</sub>

## 無料でオープンソース

- **SMTV は無料です。** プログラム全体が [MIT ライセンス](LICENSE)のオープンソースです。自分用にも、チャンネル用にも、
  クライアントの仕事にも使えますし、改変して共有することもできます。
- **透かしなし、時間の制限なし、SMTV のサブスクリプションもありません。**
- **お金がかかるのは AI だけ、それも使いたい場合だけです。** SMTV は配信のテキストを読んで見どころを選ぶために AI を必要とします。
  それはあなたのパソコン上の無料 AI でも、自分で選んだサービスでもかまいません——詳しくは下で。
- **データは手元に残ります。** クリップはあなたのパソコンで作られ、保存されます。あなたが選んだ AI に送られるのは配信のテキストだけ。
  パソコン上の無料 AI を使えば、何ひとつ外に出ません。

## AI の選び方：3 つの方法

SMTV は音声の文字起こしをあなたのパソコンで自分で行います。見どころを選ぶときは AI に尋ねます。方法をひとつ選んでください——
ひとつで十分で、**Settings → AI**（設定 → AI）でいつでも変えられます。

| | 方法 | 費用 | 向いている人 |
|---|---|---|---|
| ⭐ **アカウント経由** | StreamMoment アカウント（Google、Twitch、Telegram）でサインインして残高をチャージ。それだけです：キーも設定も不要。 | 残高から使った分だけ | すべての人：いちばん簡単な方法。録画の**リンク**を貼るときにも必要です。[ガイド](docs/guide/ja/account.md) |
| 🔑 **自分のキー** | すでに OpenAI、Claude、Gemini、OpenRouter を使っていますか？キーを貼れば、SMTV がそのまま使います。 | そのサービスに直接支払い。無料プランがあるものも | すでに AI サービスを使っている人。[キーの入手先](docs/guide/ja/get-a-key.md) |
| 💻 **無料、自分のパソコンで** | Ollama または LM Studio と Qwen モデルをインストール。SMTV が自動で見つけます。 | 無料 | 高性能なグラフィックボードのあるパソコン。クリップの出来はやや落ちます。[ガイド](docs/guide/ja/free-ai-on-your-computer.md) |

## ダウンロード

| あなたのパソコン | ダウンロード | サイズ |
|---|---|---|
| **Windows 10 または 11**（64 ビット） | [**Windows 版 SMTV**](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows-setup.exe)（インストーラー） | 約 130 MB |
| **Mac** — Apple シリコン（M1 以降）または Intel、macOS 13+ | [**Mac 版 SMTV**](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-mac.dmg) | 約 270 MB |

どの Mac でも同じ 1 つのファイルです。SMTV が Mac のプロセッサ用に作られた版を自動で起動します。Windows で何もインストールしたくないなら：
[ZIP ファイル](https://github.com/streammomenttv/smtv/releases/latest/download/SMTV-windows.zip)を展開して
**Start SMTV** を開きます。

SMTV に必要なものはすべて入っています：プログラム本体、Python、字幕付きの ffmpeg。音声認識は初回起動時に、あなたの言語の分だけ
ダウンロードされます（0.9〜2.5 GB、一度だけ）：SMTV が **Fix**（修正）ボタンひとつで提案します。

**初回はシステムに警告されます。** SMTV にはまだデジタル署名がありません：Windows 用の署名はもう少し後に、macOS 用の署名は
できるだけ早く付き、そうすればこの警告は出なくなります。それまでは：

- **Windows**（「Windows によって PC が保護されました」）：**詳細情報**（More info）→ **実行**（Run anyway）。
- **Mac**：SMTV を一度開いてから、**システム設定 → プライバシーとセキュリティ**（System Settings → Privacy & Security）→
  **このまま開く**（Open Anyway）。
- **スマート アプリ コントロール（Smart App Control）が有効な Windows 11** は、署名のないプログラムを完全にブロックし、
  通すためのボタンもありません。下の 1 行インストールを使ってください：Smart App Control が有効でも動きます。
  SMTV に署名が付けば、ダウンロード版もそこで動くようになります。

[すべてのステップを画像付きで](docs/guide/ja/install.md)。

### 経験者向け：ターミナルで 1 行

同じ SMTV を、[uv](https://astral.sh/uv) であなたのユーザーフォルダにインストールします。**Linux** でも、
**Smart App Control** が有効でも動き、同じようにウィンドウからアップデートできます。

**Windows** — スタートを押して **PowerShell** と入力し、開いて貼り付けます：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.ps1 | iex"
```

**Mac または Linux** — **ターミナル**（Terminal）を開いて貼り付けます：

```bash
curl -LsSf https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.sh | sh
```

Enter を押して数分待ちます。管理者パスワードは不要です。**SMTV** のアイコンが現れます——Windows ではデスクトップと
スタートメニューに、Mac ではアプリケーションに、Linux ではアプリケーションメニューに。

## 3 ステップで最初のクリップ

1. **AI を選ぶ** — 初回はウィンドウに 3 つの方法が表示されます（[どれにする？](docs/guide/ja/connect-ai.md)）。
2. Twitch や YouTube の録画の**リンクを貼る**か、パソコンから動画ファイルを選びます。
3. **待つ。** クリップが一本ずつ出てきます：見て、ダウンロードして、投稿。

初回、SMTV はパソコンをチェックし、足りないものを **Fix**（修正）ボタンひとつで直すよう提案します。
[最初のクリップ、ステップごとに](docs/guide/ja/first-clip.md)。

## ステップごとのガイド

こういうことが初めての人のために——すべてのステップを画像付きで：

| | |
|---|---|
| [Windows、Mac、Linux へのインストール](docs/guide/ja/install.md) | システムに警告されたときの対処も |
| [最初のクリップ](docs/guide/ja/first-clip.md) | リンクやファイルから完成したクリップまで |
| [どの AI を選ぶか](docs/guide/ja/connect-ai.md) | 3 つの方法を並べて比較 |
| [パソコンで動く無料 AI](docs/guide/ja/free-ai-on-your-computer.md) | Ollama または LM Studio と Qwen：グラフィックボードに合うモデルは |
| [キーの入手先](docs/guide/ja/get-a-key.md) | 無料または安いプランがあるサービス、ステップごとに |
| [StreamMoment アカウント](docs/guide/ja/account.md) | サインイン、残高 |
| [スマホで SMTV](docs/guide/ja/phone.md) | QR コードを読み取って、スマホでクリップを見る |
| [音声と言語](docs/guide/ja/speech-and-languages.md) | SMTV が理解できる言語 |
| [アップデートと削除](docs/guide/ja/update-and-remove.md) | |
| [うまくいかないとき](docs/guide/ja/troubleshooting.md) | パソコンのチェック、**Fix**、**Report a problem** |

## SMTV と他のツールの比較

よく使われているオープンソースのクリップ作成ツールを、各プロジェクト自身のコードとドキュメントをもとに比較しました（**2026 年 11 月時点**）。
どれも良いプロジェクトで、それぞれ別の目的のために作られています。この表は SMTV がどこで違うかを示すだけです。変わった点がありましたか？
[教えてください](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml)。表を直します。

| | **SMTV** | [openshorts](https://github.com/mutonby/openshorts) | [SupoClip](https://github.com/FujiwaraChoki/supoclip) | [PeakCut](https://github.com/haziqahmedqasmi/PeakCut) | [FunClip](https://github.com/modelscope/FunClip) |
|---|---|---|---|---|---|
| ライセンス | **MIT** | MIT（`cloud/` フォルダは独自ライセンス） | 非商用のソースライセンス | MIT | MIT |
| 6〜12 時間の配信をまるごと | **対応** | 初期設定で 1 ジョブ 60 分 | 初期設定で 90 分 | 長さの制限は明記なし | 配信向けではない |
| 配信全体の長いまとめ動画 | **あり、20〜30 分** | なし | なし（その「recap」は短いクリップ 1 本） | なし | なし |
| ロシア語の音声 | **GigaAM-v3、ロシア語専用** | Whisper または Parakeet v3 | AssemblyAI または Whisper | 非対応（Parakeet v2、英語のみ） | 非対応（中国語と英語） |
| 縦型画面に配信者の Web カメラ | **あり** | なし | ゲームモード、初期設定ではオフ | あり | 縦型クリップなし |
| 初期設定の文字起こし | **自分のパソコンで、無料** | 自分のパソコンで | AssemblyAI、有料サービス | 自分のパソコンで | 自分のパソコンで |
| 起動のしかた | **専用ウィンドウとアイコン：Windows と Mac はダウンロード、または 1 行でインストール** | Docker 上の Web ページ | Docker 上の Web ページ | Web ページ | Web ページ |

## よくある質問

<details>
<summary><b>本当に無料ですか？</b></summary>

はい。SMTV 自体は無料で、制限もありません。かかる可能性があるのは見どころを選ぶ AI の費用だけです：自分のパソコンでなら無料、
あるいは選んだサービスへの支払い（StreamMoment アカウント経由か、自分のキーで）です。
</details>

<details>
<summary><b>高性能なパソコンが必要ですか？</b></summary>

グラフィックボードは不要です：SMTV は普通のパソコンでも動きます。少し遅くなるだけです。NVIDIA のボードがあれば文字起こしが速くなります。
例外はパソコン上の無料 AI で、これには高性能なグラフィックボードが必要です（[どれくらい](docs/guide/ja/free-ai-on-your-computer.md)）。
ディスクの空き容量：最低 5 GB、6 時間の配信なら 20 GB。
</details>

<details>
<summary><b>どれくらい時間がかかりますか？</b></summary>

Apple シリコン搭載の Mac で、グラフィックボードなしで計測：2.35 時間の Twitch 録画で、見どころを見つけるのに約 6 分、
その後クリップ 1 本あたり約 1 分。10.7 分のまとめ動画は 6.5 分でした。リクエストを始める前に、SMTV がかかる時間の目安を表示します。
</details>

<details>
<summary><b>どの OS で動きますか？</b></summary>

Windows 10（バージョン 1809）以降の 64 ビット版、Apple シリコン搭載の Mac と Intel Mac は macOS 13 以降（Apple シリコンでは macOS 14 以降でネイティブに動作し、macOS 13 では Intel 版を Rosetta 経由で動かすため遅くなります）、
Linux（1 行でインストール）。Windows 11 と Apple シリコン搭載の Mac で確認済みです。Intel Mac（Rosetta 経由のみ）と
Linux デスクトップはまだテストしていません。
</details>

<details>
<summary><b>どの言語を理解できますか？</b></summary>

ロシア語、ヨーロッパの 25 言語、ほか数十の言語です。配信の言語は SMTV が自動で判別します。
[詳しく](docs/guide/ja/speech-and-languages.md)。
</details>

<details>
<summary><b>クライアントの仕事にクリップを使えますか？</b></summary>

はい。MIT ライセンスは商用を含むあらゆる利用を認めています：配信者向けの切り抜き、エージェンシー、自分のチャンネル。
切り抜く配信の配信者の権利は尊重してください。
</details>

<details>
<summary><b>クリップはどこに保存されますか？何かアップロードされますか？</b></summary>

クリップはあなたのパソコンに残ります。自分の動画ファイルが外に出ることはありません。リンクは StreamMoment アカウント経由で取得されます：
そのサーバーは録画を分割して SMTV に渡し、何も保存しません。配信のテキストは、あなたが選んだ AI にだけ送られます。
AI サービスのキーはあなたのパソコンに残り、ログや問題レポートに載ることはありません。
</details>

<details>
<summary><b>TikTok や YouTube に自動で投稿しますか？</b></summary>

まだしません：クリップをダウンロードして、自分で投稿してください。Settings → About → «Coming»（設定 → このアプリについて → 今後の予定）で予定されている機能を確認できます。
</details>

<details>
<summary><b>うまく動きません。</b></summary>

Settings → **Computer check** → **Fix**（設定 → パソコンのチェック → 修正）でほとんどの問題は解決します。それでもだめなら、
Settings → Computer check → **Report…**：SMTV があなたのキーを含まないレポートを用意し、GitHub のページを開きます。
自動では何も送信されません。[試してほしいこと](docs/guide/ja/troubleshooting.md)。
</details>

## SMTV の翻訳に協力する

SMTV のウィンドウは、あなたのパソコンの言語で表示されます。翻訳は [Weblate](https://hosted.weblate.org/engage/smtv/) で
みんなの手で作られています——プログラミングは不要です：ページを開いて、自分の言語を選び、何行か翻訳するだけ。
このページの各言語版は自動翻訳です。間違いを見つけたら、プルリクエストで直してください。[翻訳の仕組み](docs/translations.md)。

[![翻訳の状況](https://hosted.weblate.org/widget/smtv/multi-auto.svg)](https://hosted.weblate.org/engage/smtv/)

## StreamMoment

SMTV は [StreamMoment](https://streammoment.tv) チームが作っています。StreamMoment アカウントは、SMTV に AI を与え、
録画のリンクを貼れるようにするいちばん簡単な方法です。アカウントがなくても SMTV は使えます。

- [問題を報告](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml) · [アイデアを提案](https://github.com/streammomenttv/smtv/issues/new?template=feature.yml)
- [上級者向け](docs/advanced.md)：Docker、すべての AI サービス、音声モデル、キー、コマンド
- [変更履歴](CHANGELOG.md) · [コントリビュート](CONTRIBUTING.md) · [セキュリティ](SECURITY.md)
- SMTV を気に入りましたか？[Boosty で応援](https://boosty.to/smtv)して、リポジトリに ⭐ を付けてください——ほかの人が見つけやすくなります。

ライセンス：[MIT](LICENSE)。
