<!-- languages -->
[Русский](../troubleshooting.md) · [English](../en/troubleshooting.md) · [Қазақша](../kk/troubleshooting.md) · [Oʻzbekcha](../uz/troubleshooting.md) · [Azərbaycanca](../az/troubleshooting.md) · [Кыргызча](../ky/troubleshooting.md) · [简体中文](../zh-CN/troubleshooting.md) · [日本語](../ja/troubleshooting.md) · **한국어** · [Tiếng Việt](../vi/troubleshooting.md) · [Bahasa Indonesia](../id/troubleshooting.md) · [हिन्दी](../hi/troubleshooting.md) · [বাংলা](../bn/troubleshooting.md) · [Español](../es/troubleshooting.md) · [Português](../pt-BR/troubleshooting.md) · [Deutsch](../de/troubleshooting.md)

> 🌐 이 페이지는 자동으로 번역되었습니다. 개선에 참여해 주세요: [Weblate](https://hosted.weblate.org/engage/smtv/) · [풀 리퀘스트](https://github.com/yuriti/clipit/pulls) · [원문: Русский](../troubleshooting.md).

# 문제가 생겼어요

## 1. Computer check → Fix(컴퓨터 점검 → 수정)

**Settings → Computer check**(설정 → 컴퓨터 점검)는 SMTV에 필요한 모든 것을 살펴보고, 무엇이 괜찮고 무엇이 아닌지 한 줄씩 알려 줍니다.
문제 옆에는 **Fix** 버튼이 있습니다: SMTV가 스스로 할 수 있는 것을 설치하거나 고치고, 무엇을 하는지 보여 줍니다.

<img src="../../images/check.png" alt="Settings → Computer check: 줄마다 상태와 Fix 버튼" width="820">

| 줄에 나오는 내용 | 할 일 |
|---|---|
| **Video (ffmpeg)**가 없음 | **Fix**를 누르세요: SMTV가 쓰는 동영상 도구 ffmpeg를 설치합니다. |
| **Captions**(자막)가 작동하지 않음 | **Fix**를 누르세요: SMTV가 자막을 그릴 수 있는 ffmpeg를 설치합니다. |
| **AI**: 연결된 것이 없음 | **Settings → AI**에서 하나 고르세요 — [어떤 걸로](connect-ai.md). |
| **Connection to StreamMoment**(StreamMoment 연결) 실패 | 인터넷을 확인하세요. VPN이나 방화벽이 막고 있을 수 있습니다. 연결이 없어도 파일은 작동합니다. |
| **Free space**(여유 공간)가 부족함 | 디스크 공간을 비우세요: 6시간 방송은 처리하는 동안 약 20 GB가 필요합니다. |
| **Speech to text**: 모델이 다운로드되지 않음 | 첫 요청 때 저절로 다운로드됩니다. 또는 **Settings → Speech to text**에서 **Download**를 누르세요. |

관리자 비밀번호가 필요한 수정은 절대 몰래 실행되지 않습니다: SMTV가 명령이 담긴 터미널을 열어 무엇을 하는지 보여 줍니다.

## 2. 흔한 문제

- **링크가 작동하지 않아요.** 링크에는 [StreamMoment 계정](account.md)이 필요합니다. 계정이 없나요? 녹화본을 직접 다운로드해서
  SMTV에 파일로 넣으세요.
- **클립이 없거나 아주 적어요.** SMTV는 AI가 좋다고 평가한 순간만 남깁니다. 짧거나 조용한 방송은 적게 나올 수 있습니다.
  내 컴퓨터의 무료 AI는 클라우드 AI보다 좋은 순간을 적게 찾습니다.
- **"요청이 너무 많음"(«Too many requests»).** AI 서비스의 무료 요금제가 한도에 닿았습니다: 기다리거나, 유료 요금제나 계정을 쓰세요.
- **휴대폰에서 SMTV가 안 열려요.** 같은 Wi-Fi, VPN 없음, 방화벽에서 SMTV 허용 — [휴대폰](phone.md)을 보세요.
- **Windows: 터미널이 `smtv`를 거부해요.** 스마트 앱 컨트롤 때문입니다. 아이콘으로 SMTV를 실행하세요.
- **창과 SMTV의 연결이 끊겼어요.** 창을 닫고 SMTV를 다시 여세요.

멈춘 요청은 이어서 할 수 있습니다: **Continue**(계속)를 누르세요 — SMTV가 같은 단계부터 다시 시작하고, 이미 끝난 일은 다시 하지 않습니다.

## 3. 문제 신고하기

그래도 안 되나요? 알려 주세요 — 모두에게 도움이 됩니다.

1. **Settings → Computer check → Report a problem**(설정 → 컴퓨터 점검 → 문제 신고)(**Report…** 버튼; **Settings → About**에도 있습니다),
   또는 실패한 요청 아래의 버튼.
2. SMTV가 보고서에 들어갈 내용을 보여 줍니다: 버전, 컴퓨터 점검 결과, 설정, 로그. **키와 토큰은 잘려 나가고**, 홈 폴더는 `~`로 표시됩니다.
   링크와 파일 이름은 체크 상자를 선택하지 않으면 들어가지 않습니다.
3. **Save and open GitHub**(저장하고 GitHub 열기)를 누릅니다. SMTV가 압축 파일을 저장하고, 요약이 채워진 새 issue가 브라우저에서 열립니다.
   압축 파일을 거기로 끌어다 놓고 **Submit**을 누르세요.

SMTV는 저절로 아무것도 보내지 않습니다. 창 없이 하려면: 터미널에서 `smtv report`를 실행하세요.
[issue를 직접 열](https://github.com/yuriti/clipit/issues/new?template=bug.yml) 수도 있습니다.
