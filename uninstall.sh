#!/usr/bin/env bash
# VRLeft - uninstaller (keeps your settings unless --purge is given)
set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
AUTOSTART_DIR="${HOME}/.config/autostart"
UDEV_RULE_DST="/etc/udev/rules.d/60-vrleft-input.rules"
APP_NAME="VRLeft"
PURGE=0

for arg in "$@"; do
  case "$arg" in
    --purge) PURGE=1 ;;
    -h|--help)
      echo "Usage: ./uninstall.sh [--purge]   (--purge also removes settings)"
      exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

info() { printf '  \033[32mOK\033[0m  %s\n' "$1"; }

echo "VRLeft uninstaller"
echo "------------------"

rm -f "${BIN_DIR}/${APP_NAME}" && info "removed ${BIN_DIR}/${APP_NAME}"
rm -f "${APP_DIR}/vrleft.desktop" && info "removed desktop entry"
rm -f "${AUTOSTART_DIR}/vrleft-monitor.desktop" && info "removed autostart entry"

if [[ -f "${UDEV_RULE_DST}" ]] && command -v sudo >/dev/null 2>&1; then
  if sudo rm -f "${UDEV_RULE_DST}"; then
    sudo udevadm control --reload-rules 2>/dev/null || true
    info "removed ${UDEV_RULE_DST}"
  fi
fi

if [[ ${PURGE} -eq 1 ]]; then
  rm -rf "${HOME}/.config/vrleft" "${HOME}/.local/state/vrleft"
  info "removed settings and state"
else
  echo "  ..  settings kept (~/.config/vrleft, use --purge to delete)"
fi

echo "Done."
