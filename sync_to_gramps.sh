#!/usr/bin/env bash

set -euo pipefail

SOURCE="."
DEST="${1:-$HOME/projects/gramps/addons-source/NameSuite}"

# Enable with:
#   DRY_RUN=1 ./sync.sh
DRY_RUN="${DRY_RUN:-0}"

# Files and directories to sync.
#
# For directories, rsync's "***" pattern means:
#   include the directory and everything below it.
INCLUDES=(
    "name_processor/***"
    "tests/***"
    "name_processor.gpr.py"
    "names_tool.py"
    "patronymics_gramplet.py"
    "MANIFEST"
    "po/***"
)

RSYNC_ARGS=(
    -av
    --delete
    --exclude="__pycache__/"
    --exclude="*.pyc"
)

if [[ "$DRY_RUN" == "1" ]]; then
    RSYNC_ARGS+=(--dry-run)
fi

# WARNING:
# --delete removes files from DEST that are not part of the transfer set.
#
# Example:
#   ./sync.sh
#
# Custom destination:
#   ./sync.sh /tmp/NameSuite
#
# Dry run:
#   DRY_RUN=1 ./sync.sh

declare -A seen
FILTERS=()

add_filter() {
    local rule="$1"

    if [[ -z "${seen[$rule]+x}" ]]; then
        FILTERS+=("$rule")
        seen["$rule"]=1
    fi
}

for item in "${INCLUDES[@]}"; do
    add_filter "--include=$item"

    parent="$item"

    while [[ "$parent" == */* ]]; do
        parent="${parent%/*}"
        add_filter "--include=$parent/"
    done
done

add_filter "--exclude=*"

mkdir -p "$DEST"

rsync \
    "${RSYNC_ARGS[@]}" \
    "${FILTERS[@]}" \
    "$SOURCE/" \
    "$DEST/"
