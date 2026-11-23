#!/bin/sh
# SMTV installer for macOS and Linux: uv (the official way), then SMTV with its tools, then the SMTV icon.
#
#   curl -LsSf https://raw.githubusercontent.com/streammomenttv/smtv/main/install/install.sh | sh
#
# Everything goes into your own home folder: no sudo, no administrator password. Read it before running it — it is short.
#
# Options (after `sh -s --` when piped):
#   --dry-run       print what would run, change nothing
#   --no-start      do not open SMTV at the end
#   --tools LIST    which tools, comma-separated (default: vodcut)
# The same through the environment: SMTV_DRY_RUN=1, SMTV_NO_START=1, SMTV_TOOLS=vodcut, SMTV_LANG=en|ru.
set -eu

UV_INSTALLER="https://astral.sh/uv/install.sh"   # uv's official installer (Astral)
PYTHON_VERSION="3.12"                            # every dependency (onnxruntime, pywebview) has wheels for it; uv fetches it if missing
TOOLS="${SMTV_TOOLS:-vodcut}"
DRY_RUN="${SMTV_DRY_RUN:-0}"
NO_START="${SMTV_NO_START:-0}"

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --no-start) NO_START=1 ;;
    --tools) shift; TOOLS="${1:-}" ;;
    --tools=*) TOOLS="${1#--tools=}" ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

case "$TOOLS" in
  ''|*[!a-z0-9,-]*) echo "--tools: only names like vodcut or vodcut,livecut" >&2; exit 2 ;;
esac

# --- language: Russian when the system speaks Russian, English otherwise ------------------------------------------------
LANG_CODE="${SMTV_LANG:-}"
if [ -z "$LANG_CODE" ]; then
  for v in "${LC_ALL:-}" "${LC_MESSAGES:-}" "${LANG:-}"; do
    if [ -n "$v" ]; then LANG_CODE="$v"; break; fi
  done
  if [ -z "$LANG_CODE" ] && [ "$(uname -s)" = "Darwin" ]; then
    LANG_CODE="$(defaults read -g AppleLanguages 2>/dev/null | sed -n '2p' | tr -d ' ",' || true)"
  fi
fi
case "$LANG_CODE" in ru*|RU*) RU=1 ;; *) RU=0 ;; esac

say() {  # say "English" "Русский"
  if [ "$RU" = 1 ]; then printf '%s\n' "$2"; else printf '%s\n' "$1"; fi
}
fail() {
  say "$1" "$2" >&2
  exit 1
}
run() {  # prints the command, runs it unless --dry-run
  printf '  $ %s\n' "$*"
  if [ "$DRY_RUN" != 1 ]; then "$@"; fi
}

# --- this computer -----------------------------------------------------------------------------------------------------
OS="$(uname -s)"
case "$OS" in
  Darwin)
    MAC_VERSION="$(sw_vers -productVersion 2>/dev/null || echo 0)"
    if [ "${MAC_VERSION%%.*}" -lt 13 ] 2>/dev/null; then
      fail "SMTV needs macOS 13 or newer (this Mac has $MAC_VERSION). Update macOS in System Settings, then run this again." \
           "SMTV нужна macOS 13 или новее (здесь $MAC_VERSION). Обновите macOS в «Системных настройках» и запустите установку снова."
    fi ;;
  Linux) ;;
  *) fail "This installer is for macOS and Linux. On Windows run install.ps1 (see README)." \
          "Этот установщик — для macOS и Linux. На Windows запустите install.ps1 (см. README)." ;;
esac

if [ "$(id -u)" = 0 ] && [ "${SMTV_ALLOW_ROOT:-0}" != 1 ]; then
  fail "Please run this as yourself, not with sudo: SMTV installs into your own home folder." \
       "Запустите установку от своего имени, без sudo: SMTV ставится в вашу домашнюю папку."
fi

say "Installing SMTV — clips and a recap from stream recordings." "Устанавливаю SMTV — клипы и пересказ из записи стрима."
[ "$DRY_RUN" = 1 ] && say "(dry run: nothing is changed)" "(проверка: ничего не меняется)"

# --- 1. uv -------------------------------------------------------------------------------------------------------------
find_uv() {
  if command -v uv >/dev/null 2>&1; then command -v uv; return 0; fi
  for d in "${UV_INSTALL_DIR:-}" "${XDG_BIN_HOME:-}" "$HOME/.local/bin" "$HOME/.cargo/bin"; do
    if [ -n "$d" ] && [ -x "$d/uv" ]; then printf '%s\n' "$d/uv"; return 0; fi
  done
  return 1
}

UV="$(find_uv || true)"
if [ -n "$UV" ]; then
  say "1/3 uv is already here: $UV" "1/3 uv уже есть: $UV"
else
  say "1/3 Installing uv, the Python package manager (from astral.sh, its official installer)…" \
      "1/3 Ставлю uv — менеджер пакетов Python (с astral.sh, официальный установщик)…"
  if command -v curl >/dev/null 2>&1; then
    printf '  $ curl -LsSf %s | sh\n' "$UV_INSTALLER"
    [ "$DRY_RUN" = 1 ] || curl -LsSf "$UV_INSTALLER" | sh
  elif command -v wget >/dev/null 2>&1; then
    printf '  $ wget -qO- %s | sh\n' "$UV_INSTALLER"
    [ "$DRY_RUN" = 1 ] || wget -qO- "$UV_INSTALLER" | sh
  else
    fail "Neither curl nor wget is installed. Install one of them with your system's package manager, then run this again." \
         "Нет ни curl, ни wget. Поставьте один из них через менеджер пакетов системы и запустите установку снова."
  fi
  UV="$(find_uv || true)"
  if [ -z "$UV" ]; then
    if [ "$DRY_RUN" = 1 ]; then UV="$HOME/.local/bin/uv"; else
      fail "uv was installed but cannot be found. Open a new terminal window and run this installer again." \
           "uv установлен, но не найден. Откройте новое окно терминала и запустите установку снова."
    fi
  fi
fi

# --- 2. SMTV -----------------------------------------------------------------------------------------------------------
SPEC="smtv[$TOOLS]"
say "2/3 Installing $SPEC (a few minutes the first time: about 0.7 GB to download)…" \
    "2/3 Ставлю $SPEC (в первый раз несколько минут: скачивается около 0,7 ГБ)…"
if ! run "$UV" tool install --upgrade --python "$PYTHON_VERSION" "$SPEC"; then
  fail "Could not install SMTV. Check the internet connection and run this again; if it fails again, copy the text above into a problem report: https://github.com/streammomenttv/smtv/issues/new?template=bug.yml" \
       "Не удалось установить SMTV. Проверьте интернет и запустите установку снова; если не выйдет — скопируйте текст выше в сообщение о проблеме: https://github.com/streammomenttv/smtv/issues/new?template=bug.yml"
fi
# Where uv puts commands (~/.local/bin) goes on PATH for new terminals; harmless when it already is.
run "$UV" tool update-shell || true

# --- 3. the SMTV icon --------------------------------------------------------------------------------------------------
BIN_DIR="$("$UV" tool dir --bin 2>/dev/null || printf '%s' "$HOME/.local/bin")"
SMTV="$BIN_DIR/smtv"
say "3/3 Making the SMTV icon…" "3/3 Создаю значок SMTV…"
if run "$SMTV" shortcut; then
  ICON=1
else
  ICON=0
  say "The icon could not be made here (a computer without a desktop?). Start SMTV with: smtv app" \
      "Значок создать не удалось (компьютер без рабочего стола?). Запускайте SMTV командой: smtv app"
fi

say "" ""
say "SMTV is installed." "SMTV установлен."
if [ "$OS" = Darwin ]; then
  say "Start it from Applications → SMTV (or Launchpad). The first launch may take a minute." \
      "Запускайте из «Программы» → SMTV (или Launchpad). Первый запуск может занять минуту."
else
  say "Start it from the applications menu → SMTV, or run: smtv app" \
      "Запускайте из меню приложений → SMTV или командой: smtv app"
fi
say "In SMTV: choose an AI, paste a link to a stream recording, wait for the clips. Settings → Computer check finds and fixes what is missing (ffmpeg, for example)." \
    "В SMTV: выберите нейросеть, вставьте ссылку на запись стрима, дождитесь клипов. «Настройки → Проверка компьютера» найдёт и поставит недостающее (например, ffmpeg)."

if [ "$NO_START" != 1 ] && [ "$ICON" = 1 ]; then
  if [ "$OS" = Darwin ] && [ -d "$HOME/Applications/SMTV.app" ]; then
    run open "$HOME/Applications/SMTV.app" || true
  elif [ "$OS" = Linux ] && { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; }; then
    printf '  $ %s app &\n' "$SMTV"
    [ "$DRY_RUN" = 1 ] || (nohup "$SMTV" app >/dev/null 2>&1 &)
  fi
fi
