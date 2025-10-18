#!/bin/bash

set -euo pipefail

BRANCH="${1:-main}"

echo ">>> clone --branch ${BRANCH} ."

REPO_URL="https://github.com/Mdwiki-TD/svg_translate.git"

TARGET_DIR="$HOME/www/python/src"

CLONE_DIR="$HOME/temp_clone_path"

# Navigate to the project directory
cd "$HOME" || exit

# Remove temporary clone directory if it exists
rm -rf "$CLONE_DIR"

backup_dir="$HOME/www/python/src_backup_$(date +%Y%m%d_%H%M%S)"

# Try to clone the repository into a temporary folder
if git clone --branch "$BRANCH" "$REPO_URL" "$CLONE_DIR"; then
    echo "Repository cloned successfully."

else
    echo "Failed to clone repository. No changes made." >&2
    exit 1
fi

# Backup the current source if it exists
if [ -d "$TARGET_DIR" ]; then
    echo "Backing up current source to: $backup_dir"
    mv "$TARGET_DIR" "$backup_dir"
fi

# Move the new source into the target directory
if [ -d "$CLONE_DIR/src" ]; then
    mv "$CLONE_DIR/src" "$TARGET_DIR"
else
    mv "$CLONE_DIR" "$TARGET_DIR"
fi

# Remove unused template file
rm -f "$TARGET_DIR/service.template"

# Activate the virtual environment and install dependencies

if source "$HOME/www/python/venv/bin/activate"; then
    pip install -r "$TARGET_DIR/requirements.txt"
else
    echo "Failed to activate virtual environment" >&2
fi

# webservice python3.11 restart

# toolforge-jobs run updatex --image python3.11 --command "$HOME/web_sh/update.sh webservice"
