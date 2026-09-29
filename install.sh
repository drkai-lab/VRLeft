#!/usr/bin/env bash
# VRLeft (ぶいあーるれふと) - Linux / macOS installer
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
AUTOSTART_DIR="${HOME}/.config/autostart"
UDEV_RULE_SRC="${SRC_DIR}/60-vrleft-input.rules"
UDEV_RULE_DST="/etc/udev/rules.d/60-vrleft-input.rules"
APP_NAME="VRLeft"

ADD_AUTOSTART=0
SKIP_UDEV=0
INPUT_GROUP=0

for arg in "$@"; do
  case "$arg" in
    --autostart) ADD_AUTOSTART=1 ;;
    --no-udev) SKIP_UDEV=1 ;;
    --input-group) INPUT_GROUP=1 ;;
    -h|--help)
      cat <<EOF
VRLeft installer

Usage: ./install.sh [options]
  --autostart    start the monitor daemon at login
  --input-group  add this user to the "input" group (Shift+1..0 on all keyboards)
  --no-udev      skip the udev rule (already installed / no sudo)
  -h, --help     this text
EOF
      exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

info() { printf '  \033[32mOK\033[0m  %s\n' "$1"; }
warn() { printf '  \033[33m!!\033[0m  %s\n' "$1"; }
fail() { printf '  \033[31mNG\033[0m  %s\n' "$1" >&2; }

echo "VRLeft installer"
echo "----------------"

OS_NAME="$(uname -s 2>/dev/null || echo unknown)"

# --- dependencies ----------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 not found"
  exit 1
fi
info "python3 $(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"

if python3 -c 'import tkinter' >/dev/null 2>&1; then
  info "tkinter (GUI, $(python3 -c 'import tkinter; print("Tk %s" % tkinter.TkVersion)'))"
else
  fail "tkinter missing (required for the GUI)"
  echo "       Arch:    sudo pacman -S tk"
  echo "       Debian:  sudo apt install python3-tk"
  echo "       macOS:   brew install python-tk"
  exit 1
fi

# --- binary ----------------------------------------------------------------
mkdir -p "${BIN_DIR}"
install -m 0755 "${SRC_DIR}/${APP_NAME}" "${BIN_DIR}/${APP_NAME}"
info "installed ${BIN_DIR}/${APP_NAME}"

# --- desktop entry ---------------------------------------------------------
if [[ "${OS_NAME}" == "Darwin" ]]; then
  echo "  ..  desktop entry skipped (macOS uses the terminal / Finder)"
else
  mkdir -p "${APP_DIR}"
  cp "${SRC_DIR}/packaging/vrleft.desktop" "${APP_DIR}/vrleft.desktop"
  sed -i "s|^Exec=.*|Exec=${BIN_DIR}/${APP_NAME}|" "${APP_DIR}/vrleft.desktop"
  command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "${APP_DIR}" >/dev/null 2>&1 || true
  info "installed ${APP_DIR}/vrleft.desktop"
fi

# --- optional monitor autostart -------------------------------------------
if [[ "${OS_NAME}" == "Darwin" ]]; then
  echo "  ..  autostart on macOS: add a LaunchAgent (see README)"
elif [[ ${ADD_AUTOSTART} -eq 1 ]]; then
  mkdir -p "${AUTOSTART_DIR}"
  cat > "${AUTOSTART_DIR}/vrleft-monitor.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=VRLeft Monitor
Exec=${BIN_DIR}/${APP_NAME} --monitor
X-GNOME-Autostart-enabled=true
EOF
  info "monitor autostart enabled (${AUTOSTART_DIR})"
else
  echo "  ..  monitor autostart skipped (use --autostart to enable)"
fi

# --- udev rule -------------------------------------------------------------
if [[ "${OS_NAME}" != "Linux" ]]; then
  echo "  ..  udev not used on ${OS_NAME}"
elif [[ ${SKIP_UDEV} -eq 0 ]]; then
  if [[ -f "${UDEV_RULE_SRC}" ]]; then
    if command -v sudo >/dev/null 2>&1; then
      if sudo -n cp "${UDEV_RULE_SRC}" "${UDEV_RULE_DST}" 2>/dev/null || \
         sudo cp "${UDEV_RULE_SRC}" "${UDEV_RULE_DST}"; then
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        info "udev rule installed (${UDEV_RULE_DST})"
      else
        fail "could not install the udev rule - run manually:"
        echo "       sudo cp ${UDEV_RULE_SRC} ${UDEV_RULE_DST}"
        echo "       sudo udevadm control --reload-rules && sudo udevadm trigger"
      fi
    else
      fail "sudo not available - install the udev rule manually"
    fi
  else
    fail "60-vrleft-input.rules not found next to install.sh"
  fi
else
  echo "  ..  udev rule skipped (--no-udev)"
fi

# --- input group (Shift+1..0 on every keyboard) ---------------------------
if [[ "${OS_NAME}" != "Linux" ]]; then
  echo "  ..  input group not used on ${OS_NAME}"
elif [[ ${INPUT_GROUP} -eq 1 ]]; then
  if id -nG "${USER}" | tr ' ' '\n' | grep -qx "input"; then
    info "user ${USER} is already in the input group"
  elif command -v sudo >/dev/null 2>&1; then
    sudo usermod -aG input "${USER}"
    warn "added ${USER} to the input group - log out and back in to apply"
  else
    fail "could not add ${USER} to the input group (no sudo)"
  fi
else
  echo "  ..  input group skipped (use --input-group for Shift+1..0 everywhere)"
fi

# --- self test -------------------------------------------------------------
echo
if "${BIN_DIR}/${APP_NAME}" --selftest; then
  echo
  echo "Install complete. Start with:"
  echo "  ${APP_NAME}                 # configuration GUI"
  echo "  ${APP_NAME} --monitor       # input -> VRChat OSC daemon"
  exit 0
else
  echo
  echo "Install finished, but the self test reported problems (see above)."
  echo "If the input nodes show 'Permission denied', replug the keypad and"
  echo "run: ${APP_NAME} --selftest"
  exit 1
fi
