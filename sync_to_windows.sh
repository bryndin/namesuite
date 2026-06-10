#!/bin/bash
# Replace <USER> and <GRAPMPS_VER> with your actual Windows values
USER=""
GRAPMPS_VER="gramps60"

if [ -z "${USER}" ]; then
  echo "Error: USER variable is not set."
  exit 1
fi

if [ -z "${GRAPMPS_VER}" ]; then
  echo "Error: GRAPMPS_VER variable is not set."
  exit 1
fi

WINDOWS_PLUGINS_PATH="/mnt/c/Users/${USER}/AppData/Roaming/gramps/${GRAPMPS_VER}/plugins/PatronymicInference"

echo "Syncing plugin files to Windows AppData..."
mkdir -p "$WINDOWS_PLUGINS_PATH"
rsync -av --delete --exclude '.git/' --exclude 'sync_to_windows.sh' --exclude '.venv/' ./ "$WINDOWS_PLUGINS_PATH/"
echo "Sync complete."
