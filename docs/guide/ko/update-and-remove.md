<!-- languages -->
[English](../update-and-remove.md) · [Русский](../ru/update-and-remove.md) · [Қазақша](../kk/update-and-remove.md) · [Oʻzbekcha](../uz/update-and-remove.md) · [Azərbaycanca](../az/update-and-remove.md) · [Кыргызча](../ky/update-and-remove.md) · [简体中文](../zh-CN/update-and-remove.md) · [日本語](../ja/update-and-remove.md) · **한국어** · [Tiếng Việt](../vi/update-and-remove.md) · [Bahasa Indonesia](../id/update-and-remove.md) · [हिन्दी](../hi/update-and-remove.md) · [বাংলা](../bn/update-and-remove.md) · [Español](../es/update-and-remove.md) · [Português](../pt-BR/update-and-remove.md) · [Deutsch](../de/update-and-remove.md)

> 🌐 이 페이지는 자동으로 번역되었습니다. 개선에 참여해 주세요: [Weblate](https://hosted.weblate.org/engage/smtv/) · [풀 리퀘스트](https://github.com/streammomenttv/smtv/pulls).

# 업데이트와 삭제

## 업데이트

SMTV는 하루에 한 번 새 버전을 확인합니다(끌 수 있습니다). 새 버전이 있으면 **Version … is available**(버전 …을(를) 사용할 수 있습니다)이라고
알려 줍니다: **Update**(업데이트)를 누르세요.

- SMTV가 닫히고, 업데이트되고, 저절로 다시 열립니다. 보통 1분 안에 끝납니다.
- 요청이 진행 중이면 업데이트는 끝날 때까지 기다립니다 — 또는 **Stop the jobs and update**(작업을 멈추고 업데이트)를 누르세요.
  그 뒤 **Continue**로 같은 단계부터 작업을 이어 갑니다.
- 새 버전이 시작되지 않으면 이전 버전이 저절로 돌아옵니다.
- 새 버전에는 SMTV 제작자가 서명합니다. SMTV는 설치 전에 서명을 확인합니다.

업데이트에 관한 모든 것은 **Settings → Computer check → Updates**(설정 → 컴퓨터 점검 → 업데이트)에 있습니다.

Windows용이나 Mac용 SMTV를 다운로드했나요? **Update**(업데이트)는 새 설치 프로그램을 다운로드해 확인한 뒤 엽니다: 거기서 설치를
마치세요(Mac에서는 새 SMTV를 응용 프로그램으로 끌어다 놓고 **대치**(Replace)를 누릅니다). ZIP으로 받은 Windows 사본은
스스로 업데이트되지 않습니다: [릴리스 페이지](https://github.com/streammomenttv/smtv/releases/latest)에서 새 ZIP을 다운로드하세요.

SMTV를 다른 방법으로 설치했나요? Docker에서는 새 버전이 곧 새 이미지입니다. [고급 사용자용](../../advanced.md#docker)을 보세요.

## 삭제

**Settings → Computer check → Remove SMTV from this computer**(이 컴퓨터에서 SMTV 제거)(**Remove…** 버튼)는 프로그램과 SMTV 아이콘을 삭제합니다.
클립은 남습니다 — 클립도 지우려면 **Also remove clips, jobs, settings and keys**(클립, 작업, 설정, 키도 삭제)에 체크하세요.

Windows용이나 Mac용 SMTV를 다운로드했나요? 프로그램 자체는 시스템 방식으로 삭제하세요(위의 버튼은 체크한 경우 클립과 설정만
삭제합니다):

- **Windows:** **설정 → 앱 → 설치된 앱 → SMTV → 제거**(Settings → Apps → Installed apps → SMTV → Uninstall).
  ZIP으로 받은 사본은 그 폴더를 삭제하면 됩니다.
- **Mac:** **SMTV**를 **응용 프로그램**(Applications)에서 **휴지통**(Trash)으로 끌어다 놓으세요.

터미널에서 한 줄로 설치했나요? 창 없이, 터미널에서:

```bash
smtv uninstall
```

`--data`를 붙이면 클립과 설정도 삭제됩니다. 직접 설치한 프로그램(Ollama, LM Studio)은 남습니다: 다른 프로그램처럼 삭제하세요.
