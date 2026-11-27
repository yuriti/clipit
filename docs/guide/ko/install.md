<!-- languages -->
[Русский](../install.md) · [English](../en/install.md) · [Қазақша](../kk/install.md) · [Oʻzbekcha](../uz/install.md) · [Azərbaycanca](../az/install.md) · [Кыргызча](../ky/install.md) · [简体中文](../zh-CN/install.md) · [日本語](../ja/install.md) · **한국어** · [Tiếng Việt](../vi/install.md) · [Bahasa Indonesia](../id/install.md) · [हिन्दी](../hi/install.md) · [বাংলা](../bn/install.md) · [Español](../es/install.md) · [Português](../pt-BR/install.md) · [Deutsch](../de/install.md)

> 🌐 이 페이지는 자동으로 번역되었습니다. 개선에 참여해 주세요: [Weblate](https://hosted.weblate.org/engage/smtv/) · [풀 리퀘스트](https://github.com/yuriti/clipit/pulls) · [원문: Русский](../install.md).

# SMTV 설치하기

파일 하나를 다운로드해서 열면 **SMTV** 아이콘이 나타납니다. SMTV에 필요한 모든 것이 들어 있습니다. 관리자 비밀번호는 필요 없습니다.

| 내 컴퓨터 | 다운로드 | 크기 |
|---|---|---|
| **Windows 10 또는 11**(64비트) | [Windows용 SMTV](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip) | 약 130 MB |
| **Mac** — Apple 실리콘(M1 이상) 또는 Intel, macOS 13+ | [Mac용 SMTV](https://github.com/yuriti/clipit/releases/latest/download/SMTV-mac.dmg) | 약 270 MB |

모든 버전과 체크섬: [릴리스 페이지](https://github.com/yuriti/clipit/releases/latest).

**처음에 시스템이 경고하는 이유.** SMTV에는 아직 디지털 서명이 없습니다. Windows용 서명은 조금 뒤에, macOS용 서명은 최대한 빨리
붙을 예정이고, 그러면 이 경고는 사라집니다. SMTV의 코드는 공개되어 있습니다: 무엇을 하는지 누구나 읽어 볼 수 있습니다.

## Windows

1. **Windows용 SMTV**(파일 `SMTV-…-windows-x64-setup.exe`)를 다운로드해서 엽니다.
2. Windows가 파란 창 **«Windows의 PC 보호»**(Windows protected your PC)를 띄웁니다. **추가 정보**(More info)를 누른 다음
   **실행**(Run anyway)을 누릅니다.
3. 설치 프로그램이 몇 가지를 묻습니다(언어, 바탕 화면 아이콘) — **Next**(다음)와 **Install**(설치)을 누릅니다.
4. 마지막에 **Launch SMTV**(SMTV 실행)를 체크된 채로 두고 **Finish**(마침)를 누릅니다. 다음부터는 **시작** 메뉴(또는
   바탕 화면 아이콘)에서 SMTV를 실행하세요.

설치 프로그램은 SMTV를 내 사용자 폴더에 넣습니다. SMTV는 **설정 → 앱**(Settings → Apps)에 나타나며, 거기서 삭제할 수 있습니다.

**설치하지 않고:** [ZIP 파일](https://github.com/yuriti/clipit/releases/latest/download/SMTV-windows.zip)을 다운로드해
원하는 곳(예: 문서)에 압축을 풀고, `SMTV` 폴더의 **SMTV.exe**를 엽니다. 이 사본은 스스로 업데이트되지 않습니다:
새 버전은 새 ZIP입니다.

### Windows 11: 스마트 앱 컨트롤

**스마트 앱 컨트롤**(Smart App Control, Windows 보안 → 앱 및 브라우저 컨트롤)이 켜져 있으면 Windows는 서명 없는 프로그램을
완전히 차단하고, 통과시키는 버튼도 없습니다. SMTV 때문에 스마트 앱 컨트롤을 끌 필요는 없습니다. 대신 SMTV를 한 줄로
설치하세요 — 스마트 앱 컨트롤이 켜져 있어도 작동합니다: [터미널에서 한 줄로](#경험-있는-사용자용-터미널에서-한-줄로). SMTV에 서명이 붙으면
다운로드 버전도 거기서 작동합니다.

## Mac

1. **Mac용 SMTV**를 다운로드합니다. Apple 실리콘이든 Intel이든 모든 Mac에 쓰는 파일 하나입니다: SMTV가 Mac 프로세서에 맞게 만든 버전을 알아서 실행합니다.
2. 다운로드한 `.dmg`를 엽니다. SMTV와 **응용 프로그램**(Applications) 폴더가 있는 창이 열립니다: **SMTV**를
   **응용 프로그램**으로 끌어다 놓으세요.
3. **응용 프로그램**을 열고 **SMTV**를 더블클릭합니다. macOS가 SMTV를 확인할 수 없다며 열지 않습니다. **완료**(Done)를 누릅니다.
4. **시스템 설정 → 개인정보 보호 및 보안**(System Settings → Privacy & Security)을 열고 아래로 스크롤합니다. «SMTV이(가)
   차단되었습니다…» 옆의 **그래도 열기**(Open Anyway)를 누르고, Mac 암호를 입력한 뒤 **열기**(Open)를 누릅니다.
   macOS 14에서는 더 짧은 방법이 있습니다: 응용 프로그램에서 **SMTV**를 오른쪽 클릭 → **열기** → **열기**.

처음 한 번만 그렇습니다: 그 뒤로는 응용 프로그램이나 Launchpad에서 평소처럼 클릭하면 SMTV가 열립니다. 같은 단계가 `.dmg` 안의
«How to open» 파일에도 있습니다.

## 처음 실행할 때

SMTV는 컴퓨터를 점검하고 첫 클립까지의 세 단계를 보여 줍니다. 그 아래에서 **내 언어용 음성 인식** — 방송 속 말을 텍스트로 바꾸는
부분 — 을 제안합니다. 이것은 다운로드 파일에 들어 있지 않습니다. 언어마다 따로 필요하기 때문입니다(0.9–2.5 GB).
**Fix**(수정)를 누르고 진행 상황을 지켜보거나, 건너뛰어도 됩니다: 첫 요청이 알아서 다운로드합니다.

**필요한 것:** 여유 공간 최소 5 GB, 6시간 방송이라면 20 GB; 인터넷. 그래픽 카드는 필요 없습니다.

## 경험 있는 사용자용: 터미널에서 한 줄로

같은 SMTV를 [uv](https://astral.sh/uv) — Python 프로그램을 설치하는 작은 공식 도구 — 로 내 사용자 폴더에 설치합니다.
**Linux**에서, **스마트 앱 컨트롤**이 켜져 있을 때, 또는 터미널이 더 편할 때 쓰세요. 다운로드한 앱처럼 창에서 업데이트됩니다.

**Windows:** **시작**을 누르고 `PowerShell`을 입력한 뒤 **Windows PowerShell**(파란 창)을 열고, 이 줄을 붙여 넣은 다음(오른쪽
클릭 또는 Ctrl+V) **Enter**를 누릅니다:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/yuriti/clipit/main/install/install.ps1 | iex"
```

스마트 앱 컨트롤이 켜져 있으면 설치 프로그램은 python.org의 서명된 Python 위에 SMTV를 설치하고(Python 설치를 요청할 수
있습니다 — 동의하세요) 그것을 통해 SMTV를 실행합니다. 터미널에서 `smtv`를 실행할 수 없다고 나오면 대신 **SMTV** 아이콘을 쓰세요.

**Mac 또는 Linux:** **터미널**(Terminal)을 열고(Mac에서는 Cmd+Space, `Terminal` 입력, Enter), 이 줄을 붙여 넣은 다음
**Enter**를 누릅니다:

```bash
curl -LsSf https://raw.githubusercontent.com/yuriti/clipit/main/install/install.sh | sh
```

완료됐다고 나올 때까지 기다리세요(2–10분). SMTV가 저절로 열립니다. **SMTV** 아이콘은 Windows에서는 시작 메뉴에, Mac에서는
응용 프로그램에, Linux에서는 애플리케이션 메뉴에 있습니다. 이 방법으로 설치하면 SMTV가 처음에 **ffmpeg**(동영상 도구)를
**Fix**(수정)로 설치하자고 제안합니다. 위의 다운로드 버전에는 이미 들어 있습니다.

두 설치 프로그램 모두 짧고 공개되어 있습니다: [install.ps1](../../../install/install.ps1), [install.sh](../../../install/install.sh).

## 시스템이 경고할 때

- **Windows: «Windows의 PC 보호»**(Windows protected your PC, SmartScreen). **추가 정보**(More info)를 누른 다음
  **실행**(Run anyway)을 누릅니다.
- **Windows 11: 스마트 앱 컨트롤(Smart App Control)이 SMTV를 차단합니다.** SMTV에 서명이 붙을 때까지
  [터미널에서 한 줄로](#경험-있는-사용자용-터미널에서-한-줄로) 설치하세요.
- **Windows: 방화벽이** SMTV의 네트워크 사용을 허용할지 묻습니다. **개인** 네트워크에서 허용하세요: 휴대폰에서 SMTV를 열 때
  필요합니다. 휴대폰을 쓰지 않는다면 거부해도 괜찮습니다.
- **Mac: «SMTV cannot be opened»**('SMTV'을(를) 열 수 없습니다), «Apple은 …을(를) 확인할 수 없습니다» 또는 «개발자를 확인할 수
  없습니다». **시스템 설정 → 개인정보 보호 및 보안**(System Settings → Privacy & Security)을 열고 아래로 스크롤해 SMTV 옆의
  **그래도 열기**(Open Anyway)를 누릅니다.
- **Mac: «SMTV would like to accept incoming connections»**(SMTV가 수신 네트워크 연결을 허용하려고 합니다) — 휴대폰에서 SMTV를
  쓰려면 허용하세요.
- **백신 프로그램**이 경고하나요? SMTV는 새 프로그램이고 아직 서명이 없어서, 일부 백신 프로그램이 조심스럽게 다룹니다. 코드는
  공개되어 있고, 모든 파일의 체크섬은 [릴리스 페이지](https://github.com/yuriti/clipit/releases/latest)에 있습니다
  (`SHA256SUMS.txt`).

다음: [첫 클립](first-clip.md).
