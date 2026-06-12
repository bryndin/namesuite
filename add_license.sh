#!/bin/bash

# Default values
EXCLUDE_PATTERN=".*" # Default: skip hidden directories starting with a dot
TARGET_DIR=""

# Parse command line options
while getopts "e:" opt; do
    case $opt in
        e) EXCLUDE_PATTERN="$OPTARG" ;;
        *) echo "Usage: $0 [-e exclude_pattern] [target_directory]" >&2; exit 1 ;;
    esac
done
shift $((OPTIND -1))

# Handle optional root directory parameter (defaults to '.' if not provided)
TARGET_DIR="${1:-.}"

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory '$TARGET_DIR' does not exist." >&2
    exit 1
fi

# Define the license text block
LICENSE_TEXT=$(cat << 'EOF'
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2026  Dmitry Bryndin
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
EOF
)

# Find arguments to safely prune excluded paths
if [ -n "$EXCLUDE_PATTERN" ]; then
    FIND_ARGS=( "$TARGET_DIR" \( -type d -name "$EXCLUDE_PATTERN" -not -path "$TARGET_DIR" \) -prune -o -type f -name "*.py" -print )
else
    FIND_ARGS=( "$TARGET_DIR" -type f -name "*.py" )
fi

# Initialize counters for verification
files_modified=0
files_skipped=0
files_empty=0

# Find files using the built arguments array
while read -r file; do
    [ -z "$file" ] && continue

    # 1. Skip empty files (size is 0 bytes)
    if [ ! -s "$file" ]; then
        echo "Skipping (empty file): $file"
        ((files_empty++))
        continue
    fi

    # Check if the file already contains the license header to avoid duplicates
    if ! grep -q "Copyright (C) 2026  Dmitry Bryndin" "$file"; then
        echo "Adding license to: $file"
        
        tmp_file=$(mktemp)
        
        # Check if the first line is a shebang (e.g., #!/usr/bin/env python3)
        if head -n 1 "$file" | grep -q "^#!/"; then
            head -n 1 "$file" > "$tmp_file"
            echo "" >> "$tmp_file"
            echo "$LICENSE_TEXT" >> "$tmp_file"
            echo "" >> "$tmp_file"
            tail -n +2 "$file" >> "$tmp_file"
        else
            echo "$LICENSE_TEXT" > "$tmp_file"
            echo "" >> "$tmp_file"
            cat "$file" >> "$tmp_file"
        fi
        
        mv "$tmp_file" "$file"
        ((files_modified++))
    else
        echo "Skipping (already licensed): $file"
        ((files_skipped++))
    fi
done < <(find "${FIND_ARGS[@]}")

# Total files processed by the loop logic (including empty ones)
total_processed=$((files_modified + files_skipped + files_empty))

# Independent system count for verification
actual_py_count=$(find "${FIND_ARGS[@]}" | wc -l)

echo "-----------------------------------------------"
echo "Process Complete."
echo "Excluding Dirs:  $EXCLUDE_PATTERN"
echo "Files Modified:  $files_modified"
echo "Files Skipped:   $files_skipped"
echo "Files Empty:     $files_empty"
echo "Total Tracked:   $total_processed"
echo "Actual .py Files:$actual_py_count"
echo "-----------------------------------------------"

# Verification test
if [ "$total_processed" -eq "$actual_py_count" ]; then
    echo "✓ Success: The file counts match perfectly."
    exit 0
else
    echo "❌ Error: Discrepancy detected! Processed counts do not match the filesystem." >&2
    exit 1
fi