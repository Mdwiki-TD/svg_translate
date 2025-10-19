#!/bin/bash

set -euo pipefail

BRANCH="${1:-main}"

REPO_URL="https://github.com/Mdwiki-TD/svg_translate.git"

TARGET_DIR="$HOME/www/python/src"

CLONE_DIR="$HOME/temp_clone_path"

backup_dir="$HOME/www/python/src_backup_$(date +%Y%m%d_%H%M%S)"

# Navigate to the project directory
cd "$HOME" || exit


echo ">>> clone --branch ${BRANCH} ."

# Remove temporary clone directory if it exists
rm -rf "$CLONE_DIR"

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
CLONE_DIR_SRC = "$CLONE_DIR";
if [ -d "$CLONE_DIR/src" ]; then
    CLONE_DIR_SRC = "$CLONE_DIR/src";
fi

# Move the new source into the target directory
if ! mv "$CLONE_DIR_SRC" "$TARGET_DIR"; then
    echo "Failed to move cloned source to target directory" >&2
    exit 1
fi

# Remove unused template file
rm -f "$TARGET_DIR/service.template"

# Activate the virtual environment and install dependencies

if source "$HOME/www/python/venv/bin/activate"; then
    pip install -r "$TARGET_DIR/requirements.txt"
else
    echo "Failed to activate virtual environment" >&2
fi

# toolforge-webservice python3.11 restart


# become copy-svg-langs
# toolforge-webservice python3.11 shell
# source "$HOME/www/python/venv/bin/activate"
# pip install -r $HOME/www/python/src/requirements.txt


# toolforge-jobs run updatex --image python3.11 --command "$HOME/web_sh/update.sh webservice-sql" --wait
# toolforge-webservice python3.11 restart
