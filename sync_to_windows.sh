#!/bin/bash
# Replace <USER> and <GRAPMPS_VER> with your actual Windows values
USER=""
GRAMPS_VER="gramps60"

if [ -z "${USER}" ]; then
  echo "Error: USER variable is not set."
  exit 1
fi

if [ -z "${GRAMPS_VER}" ]; then
  echo "Error: GRAMPS_VER variable is not set."
  exit 1
fi

WINDOWS_PLUGINS_PATH="/mnt/c/Users/${USER}/AppData/Roaming/gramps/${GRAMPS_VER}/plugins/NameSuite"

echo "Syncing plugin files to Windows AppData..."
mkdir -p "$WINDOWS_PLUGINS_PATH"
rsync -av --delete \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --include='name_processor/' \
  --include='name_processor/***' \
  --include='name_processor.gpr.py' \
  --include='names_tool.py' \
  --include='patronymics_gramplet.py' \
  --exclude='*' \
  ./ "$WINDOWS_PLUGINS_PATH/"

echo "Sync complete."
