<!-- The source is the Russian README.md; translations: README.<language>.md, the same structure. A change to README.md
     changes README.en.md in the same PR; the other languages follow (each says it was translated automatically from
     the Russian original and links it and Weblate). Pictures: docs/images/. -->
<div align="center">

# SMTV

**긴 방송을 짧은 클립과 요약 영상으로. 무료로, 내 컴퓨터에서.**

<!-- languages -->
[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md) · [Oʻzbekcha](README.uz.md) · [Azərbaycanca](README.az.md) · [Кыргызча](README.ky.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · **한국어** · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [हिन्दी](README.hi.md) · [বাংলা](README.bn.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [Deutsch](README.de.md)

> 🌐 이 페이지는 자동으로 번역되었습니다. 개선에 참여해 주세요: [Weblate](https://hosted.weblate.org/engage/smtv/) · [풀 리퀘스트](https://github.com/yuriti/clipit/pulls) · [원문: Русский](README.md).

[![최신 릴리스](https://img.shields.io/github/v/release/yuriti/clipit?label=release)](https://github.com/yuriti/clipit/releases/latest)
[![다운로드 수](https://img.shields.io/pepy/dt/smtv?label=downloads)](https://pepy.tech/projects/smtv)
[![스타](https://img.shields.io/github/stars/yuriti/clipit?style=flat)](https://github.com/yuriti/clipit/stargazers)
[![라이선스: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/smtv)](https://pypi.org/project/smtv/)
[![Weblate에서 번역하기](https://hosted.weblate.org/widget/smtv/svg-badge.svg)](https://hosted.weblate.org/engage/smtv/)

<img src="docs/images/demo.gif" alt="SMTV: 방송 녹화본을 넣으면 SMTV가 가장 좋은 순간을 찾아 세로 클립을 하나씩 만듭니다" width="820">

[**SMTV 다운로드**](#다운로드) · [단계별 가이드](docs/guide/ko/README.md) · [다른 도구와 비교](#smtv와-다른-도구-비교) · [자주 묻는 질문](#자주-묻는-질문)

</div>

---

여섯 시간 동안 방송했습니다. 그 안 어딘가에 올릴 만한 순간이 열 개쯤 있겠지만, 그걸 찾으려면 전부 다시 봐야 합니다.
**SMTV가 대신 봐 드립니다.** Twitch나 YouTube 다시보기 링크를 붙여 넣거나 동영상 파일을 고르면, SMTV가 방송 전체를 듣고
가장 좋은 순간을 골라 TikTok, Shorts, Reels용 **바로 올릴 수 있는 세로 클립**을 만들어 줍니다. 자막이 들어가고 웹캠은 위쪽에 배치됩니다.
여기에 방송 전체를 담은 **20–30분 요약 영상**도 YouTube용으로 만들어 줍니다.

## 할 수 있는 일

| | |
|---|---|
| 🎬 **바로 올릴 수 있는 클립** | 세로 9:16, 큼직한 자막, 시작 부분의 짧은 타이틀 카드, 게임 화면 위에 스트리머의 웹캠. |
| ⏱️ **긴 방송도 문제없음** | 6–12시간 녹화본을 넣으면 최대 30개의 클립이 나옵니다. 클립은 하나씩 나오니 나머지가 끝나기 전에 올리기 시작할 수 있습니다. |
| 📺 **방송 전체 요약 영상** | YouTube용 20–30분 영상: 방송 그 자체에서 볼 만한 부분만 남긴 것입니다. |
| 🗣️ **다양한 언어** | 러시아어, 유럽 25개 언어, 그 밖의 수십 개 언어. SMTV가 내 컴퓨터에서 바로 음성을 텍스트로 바꿉니다. |
| 🔒 **파일은 내 곁에** | 클립은 내 컴퓨터에서 만들어지고 보관됩니다. 어떤 웹사이트에도 업로드되지 않습니다. |
| 💸 **무료이고 열려 있음** | MIT 라이선스: 마음껏 쓰고, 공유하고, 클라이언트 작업에도 쓰세요. 워터마크 없음, 시간 제한 없음. |

## 작동하는 모습 보기

**링크를 붙여 넣거나 파일을 고르고, 단계별로 지켜보세요.** 모든 단계가 화면에 표시됩니다: 음성을 텍스트로, 순간 찾기,
순간 평가, 클립 하나하나 편집.

<img src="docs/images/new-request.gif" alt="새 요청: 동영상 파일을 고르면 SMTV가 시작하고 모든 단계를 보여 줍니다" width="820">

**클립이 하나씩 나옵니다.** SMTV 안에서 바로 보고, 다운로드하고, 올리세요.

<img src="docs/images/clips.png" alt="방송에서 완성된 클립이 격자로 놓인 모습" width="820">

**모든 클립에는 텍스트가 함께 있습니다.** 무슨 말이 오갔는지, SMTV가 왜 그 순간을 골랐는지 읽어 보세요.

<img src="docs/images/viewer.png" alt="자막 텍스트 옆에서 재생 중인 클립" width="820">

**그리고 방송 전체 요약 영상**도 YouTube용으로, 클립 다음에 만들어집니다.

<img src="docs/images/recap.png" alt="SMTV에 표시된 방송 요약 영상" width="820">

**라이트 또는 다크** — 컴퓨터 설정에 따라.

<img src="docs/images/dark.png" alt="다크 테마의 SMTV" width="820">

<sub>이 그림 속 방송은 데모용으로 만든 것입니다: 작은 게임, 웹캠 대신 만화 마스코트, 그리고 컴퓨터 음성.
실제 사람은 화면에 나오지 않습니다.</sub>

## 무료 오픈 소스

- **SMTV는 무료입니다.** 프로그램 전체가 [MIT 라이선스](LICENSE)의 오픈 소스입니다: 나를 위해, 내 채널을 위해,
  클라이언트를 위해 쓰고, 고치고, 공유할 수 있습니다.
- **워터마크 없음, 시간 제한 없음, SMTV 구독 없음.**
- **돈은 AI에만, 그것도 원할 때만 듭니다.** SMTV는 방송의 텍스트를 읽고 순간을 고를 AI가 필요합니다.
  내 컴퓨터의 무료 AI일 수도 있고, 직접 고른 서비스일 수도 있습니다 — 아래를 보세요.
- **데이터는 내 곁에 남습니다.** 클립은 내 컴퓨터에서 만들어지고 보관됩니다. 내가 고른 AI에는 방송의 텍스트만 전달됩니다.
  내 컴퓨터의 무료 AI를 쓰면 아무것도 밖으로 나가지 않습니다.

## AI 고르기: 세 가지 방법

SMTV는 내 컴퓨터에서 음성을 직접 텍스트로 바꿉니다. 가장 좋은 순간을 고를 때는 AI에게 물어봅니다. 한 가지 방법을 고르세요 —
하나면 충분하고, **Settings → AI**(설정 → AI)에서 언제든 바꿀 수 있습니다.

| | 방법 | 비용 | 이런 분께 |
|---|---|---|---|
| ⭐ **계정으로** | StreamMoment 계정(Google, Twitch 또는 Telegram)으로 로그인하고 잔액을 충전하세요. 그게 전부입니다: 키도, 설정도 필요 없습니다. | 잔액에서 쓴 만큼 | 모두에게: 가장 간단한 방법. 녹화본 **링크**를 붙여 넣을 때도 필요합니다. [가이드](docs/guide/ko/account.md) |
| 🔑 **내 키** | 이미 OpenAI, Claude, Gemini, OpenRouter를 쓰고 있나요? 키를 붙여 넣으면 SMTV가 그대로 사용합니다. | 해당 서비스에 직접 지불; 무료 요금제가 있는 곳도 있음 | 이미 AI 서비스를 쓰는 분. [키 받는 곳](docs/guide/ko/get-a-key.md) |
| 💻 **무료, 내 컴퓨터에서** | Ollama나 LM Studio와 Qwen 모델을 설치하세요. SMTV가 알아서 찾습니다. | 무료 | 강력한 그래픽 카드가 있는 컴퓨터. 클립 품질은 조금 떨어집니다. [가이드](docs/guide/ko/free-ai-on-your-computer.md) |

## 다운로드

| 내 컴퓨터 | 다운로드 | 크기 |
|---|---|---|
| **Windows 10 또는 11**(64비트) | [**Windows용 SMTV**](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip)(설치 프로그램) | 약 130 MB |
| **Mac** — Apple 실리콘(M1 이상) 또는 Intel, macOS 13+ | [**Mac용 SMTV**](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | 약 270 MB |

모든 Mac에 파일 하나: SMTV가 Mac 프로세서에 맞게 만든 버전을 알아서 실행합니다. Windows에서 아무것도 설치하고 싶지 않다면:
[ZIP 파일](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip) — 압축을 풀고
**SMTV.exe**를 여세요.

SMTV에 필요한 모든 것이 들어 있습니다: 프로그램, Python, 자막을 넣을 수 있는 ffmpeg. 음성 인식은 처음 실행할 때 내 언어용만
다운로드됩니다(0.9–2.5 GB, 한 번만): SMTV가 **Fix**(수정) 버튼 하나로 제안합니다.

**처음에는 시스템이 경고합니다.** SMTV에는 아직 디지털 서명이 없습니다: Windows용 서명은 조금 뒤에, macOS용 서명은 최대한 빨리
붙을 예정이고, 그러면 이 경고는 사라집니다. 그때까지는:

- **Windows**(«Windows의 PC 보호»): **추가 정보**(More info) → **실행**(Run anyway).
- **Mac**: SMTV를 한 번 연 다음 **시스템 설정 → 개인정보 보호 및 보안**(System Settings → Privacy & Security) →
  **그래도 열기**(Open Anyway).
- **스마트 앱 컨트롤(Smart App Control)이 켜진 Windows 11**은 서명 없는 프로그램을 완전히 차단하고, 통과시키는 버튼도 없습니다.
  아래의 한 줄 설치를 쓰세요: Smart App Control이 켜져 있어도 작동합니다. SMTV에 서명이 붙으면 다운로드 버전도 거기서 작동합니다.

[모든 단계를 그림과 함께](docs/guide/ko/install.md).

### 경험 있는 사용자용: 터미널에서 한 줄로

같은 SMTV를 [uv](https://astral.sh/uv)로 내 사용자 폴더에 설치합니다. **Linux**에서도, **Smart App Control**이 켜져 있어도
작동하며, 똑같이 창에서 업데이트됩니다.

**Windows** — 시작을 누르고 **PowerShell**을 입력해 연 다음 붙여 넣으세요:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

**Mac 또는 Linux** — **터미널**(Terminal)을 열고 붙여 넣으세요:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

Enter를 누르고 몇 분 기다리세요. 관리자 비밀번호는 필요 없습니다. **SMTV** 아이콘이 나타납니다 — Windows에서는 바탕 화면과
시작 메뉴에, Mac에서는 응용 프로그램에, Linux에서는 애플리케이션 메뉴에.

## 세 단계로 만드는 첫 클립

1. **AI 고르기** — 처음 실행하면 창에 세 가지 방법이 나옵니다([어떤 걸로?](docs/guide/ko/connect-ai.md)).
2. Twitch나 YouTube 녹화본 **링크를 붙여 넣거나**, 컴퓨터에서 동영상 파일을 고르세요.
3. **기다리기.** 클립이 하나씩 나옵니다: 보고, 다운로드하고, 올리세요.

처음에 SMTV는 컴퓨터를 점검하고, 부족한 것을 **Fix**(수정) 버튼 하나로 고치자고 제안합니다.
[첫 클립, 단계별로](docs/guide/ko/first-clip.md).

## 단계별 가이드

이런 일이 처음인 분을 위해 — 모든 단계를 그림과 함께:

| | |
|---|---|
| [Windows, Mac, Linux에 설치하기](docs/guide/ko/install.md) | 시스템이 경고할 때 할 일도 함께 |
| [첫 클립](docs/guide/ko/first-clip.md) | 링크나 파일에서 완성된 클립까지 |
| [어떤 AI를 고를까](docs/guide/ko/connect-ai.md) | 세 가지 방법을 나란히 비교 |
| [내 컴퓨터의 무료 AI](docs/guide/ko/free-ai-on-your-computer.md) | Ollama 또는 LM Studio와 Qwen: 내 그래픽 카드에 맞는 모델은 |
| [키 받는 곳](docs/guide/ko/get-a-key.md) | 무료 또는 저렴한 요금제가 있는 서비스, 단계별로 |
| [StreamMoment 계정](docs/guide/ko/account.md) | 로그인, 잔액 |
| [휴대폰에서 SMTV](docs/guide/ko/phone.md) | QR 코드를 스캔해 휴대폰으로 클립 보기 |
| [음성과 언어](docs/guide/ko/speech-and-languages.md) | SMTV가 알아듣는 언어 |
| [업데이트와 삭제](docs/guide/ko/update-and-remove.md) | |
| [문제가 생겼어요](docs/guide/ko/troubleshooting.md) | 컴퓨터 점검, **Fix**, **Report a problem** |

## SMTV와 다른 도구 비교

사람들이 가장 많이 쓰는 오픈 소스 클리퍼를 각 프로젝트의 코드와 문서를 바탕으로 비교했습니다(**2026년 11월 기준**).
모두 좋은 프로젝트이고 저마다의 목적이 있습니다. 이 표는 SMTV가 어디서 다른지만 보여 줍니다. 바뀐 점이 있나요?
[알려 주세요](https://github.com/yuriti/clipit/issues/new?template=bug.yml). 표를 고치겠습니다.

| | **SMTV** | [openshorts](https://github.com/mutonby/openshorts) | [SupoClip](https://github.com/FujiwaraChoki/supoclip) | [PeakCut](https://github.com/haziqahmedqasmi/PeakCut) | [FunClip](https://github.com/modelscope/FunClip) |
|---|---|---|---|---|---|
| 라이선스 | **MIT** | MIT(`cloud/` 폴더는 별도 라이선스) | 비상업용 소스 라이선스 | MIT | MIT |
| 6–12시간 방송 전체 | **가능** | 기본값으로 작업당 60분 | 기본값 90분 | 길이 제한 명시 없음 | 방송용으로 만들어지지 않음 |
| 방송 전체의 긴 요약 영상 | **있음, 20–30분** | 없음 | 없음(그 «recap»은 짧은 클립 하나) | 없음 | 없음 |
| 러시아어 음성 | **GigaAM-v3, 러시아어 전용** | Whisper 또는 Parakeet v3 | AssemblyAI 또는 Whisper | 불가(Parakeet v2, 영어만) | 불가(중국어와 영어) |
| 세로 화면 속 스트리머 웹캠 | **있음** | 없음 | 게임 모드, 기본값은 꺼짐 | 있음 | 세로 클립 없음 |
| 기본 음성 텍스트 변환 | **내 컴퓨터에서, 무료** | 내 컴퓨터에서 | AssemblyAI, 유료 서비스 | 내 컴퓨터에서 | 내 컴퓨터에서 |
| 실행 방법 | **전용 창과 아이콘: Windows와 Mac은 다운로드, 또는 한 줄 설치** | Docker 안의 웹 페이지 | Docker 안의 웹 페이지 | 웹 페이지 | 웹 페이지 |

## 자주 묻는 질문

<details>
<summary><b>정말 무료인가요?</b></summary>

네. SMTV 자체는 무료이고 제한도 없습니다. 들 수 있는 비용은 순간을 고르는 AI뿐입니다: 내 컴퓨터에서는 무료,
아니면 직접 고른 서비스에 지불합니다(StreamMoment 계정이나 내 키를 통해).
</details>

<details>
<summary><b>고사양 컴퓨터가 필요한가요?</b></summary>

그래픽 카드는 필요 없습니다: SMTV는 평범한 컴퓨터에서도 돌아가고, 조금 느릴 뿐입니다. NVIDIA 카드가 있으면 음성 텍스트 변환이
빨라집니다. 내 컴퓨터의 무료 AI는 예외로, 강력한 그래픽 카드가 필요합니다([어떤 카드](docs/guide/ko/free-ai-on-your-computer.md)).
여유 디스크 공간: 최소 5 GB, 6시간 방송이라면 20 GB.
</details>

<details>
<summary><b>시간은 얼마나 걸리나요?</b></summary>

그래픽 카드 없이 Apple 실리콘 Mac에서 측정했습니다: 2.35시간짜리 Twitch 녹화본에서 순간을 찾는 데 약 6분,
그다음 클립 하나당 약 1분; 10.7분짜리 요약 영상은 6.5분 걸렸습니다. 요청을 시작하기 전에 SMTV가 예상 소요 시간을 보여 줍니다.
</details>

<details>
<summary><b>어떤 운영체제에서 돌아가나요?</b></summary>

Windows 10(버전 1809) 이상, 64비트; Apple 실리콘 Mac과 Intel Mac은 macOS 13 이상(Apple 실리콘에서는 macOS 14부터 네이티브로 실행되고, macOS 13에서는 Intel 버전을 Rosetta로 실행해 더 느립니다); Linux(한 줄 설치).
Windows 11과 Apple 실리콘 Mac에서 확인했습니다. Intel Mac(Rosetta로만 실행)과 Linux 데스크톱은 아직 테스트하지 않았습니다.
</details>

<details>
<summary><b>어떤 언어를 알아듣나요?</b></summary>

러시아어, 유럽 25개 언어, 그 밖의 수십 개 언어입니다. 방송의 언어는 SMTV가 알아서 찾아냅니다.
[자세히](docs/guide/ko/speech-and-languages.md).
</details>

<details>
<summary><b>클립을 클라이언트 작업에 써도 되나요?</b></summary>

네. MIT 라이선스는 상업적 용도를 포함한 모든 사용을 허용합니다: 스트리머를 위한 클리핑, 에이전시, 내 채널.
클리핑하는 방송의 스트리머가 가진 권리는 존중해 주세요.
</details>

<details>
<summary><b>클립은 어디로 가나요? 업로드되는 게 있나요?</b></summary>

클립은 내 컴퓨터에 남습니다. 내 동영상 파일은 절대 밖으로 나가지 않습니다. 링크는 StreamMoment 계정을 통해 가져옵니다:
그 서버가 녹화본을 조각조각 SMTV로 넘겨 주고 아무것도 저장하지 않습니다. 방송의 텍스트는 내가 고른 AI에만 전달됩니다.
AI 서비스 키는 내 컴퓨터에 남고, 로그나 문제 보고서에 절대 나타나지 않습니다.
</details>

<details>
<summary><b>TikTok이나 YouTube에 알아서 올려 주나요?</b></summary>

아직은 아닙니다: 클립을 다운로드해서 직접 올리세요. Settings → About → «Coming»(설정 → 정보 → 예정)에서 계획된 기능을 볼 수 있습니다.
</details>

<details>
<summary><b>뭔가 안 돼요.</b></summary>

Settings → **Computer check** → **Fix**(설정 → 컴퓨터 점검 → 수정)로 대부분의 문제가 해결됩니다. 그래도 안 되나요?
Settings → Computer check → **Report…**: SMTV가 내 키를 뺀 보고서를 준비하고 GitHub 페이지를 엽니다. 저절로 전송되는 것은 없습니다.
[시도해 볼 것](docs/guide/ko/troubleshooting.md).
</details>

## SMTV 번역 돕기

SMTV 창은 내 컴퓨터의 언어로 표시됩니다. 번역은 [Weblate](https://hosted.weblate.org/engage/smtv/)에서 사람들이 직접 합니다 —
프로그래밍은 필요 없습니다: 페이지를 열고, 내 언어를 고르고, 몇 줄 번역하면 됩니다. 이 페이지의 번역본은 자동으로 만들어졌습니다.
실수를 발견하면 풀 리퀘스트로 고쳐 주세요. [번역은 어떻게 이루어지나요](docs/translations.md).

[![번역 현황](https://hosted.weblate.org/widget/smtv/multi-auto.svg)](https://hosted.weblate.org/engage/smtv/)

## StreamMoment

SMTV는 [StreamMoment](https://streammoment.tv) 팀이 만듭니다. StreamMoment 계정은 SMTV에 AI를 연결하고
녹화본 링크를 붙여 넣는 가장 간단한 방법입니다. 계정이 없어도 SMTV는 작동합니다.

- [문제 신고](https://github.com/yuriti/clipit/issues/new?template=bug.yml) · [아이디어 제안](https://github.com/yuriti/clipit/issues/new?template=feature.yml)
- [고급 사용자용](docs/advanced.md): Docker, 모든 AI 서비스, 음성 모델, 키, 명령어
- [변경 사항](CHANGELOG.md) · [기여하기](CONTRIBUTING.md) · [보안](SECURITY.md)
- SMTV가 마음에 드나요? [Boosty에서 후원](https://boosty.to/smtv)하고 저장소에 ⭐를 눌러 주세요 — 다른 사람들이 찾는 데 도움이 됩니다.

라이선스: [MIT](LICENSE).
