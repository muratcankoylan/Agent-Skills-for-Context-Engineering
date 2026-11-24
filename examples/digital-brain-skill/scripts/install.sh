#!/bin/bash
# Digital Brain Installation Script
# Installs Digital Brain as a Claude Code skill

set -e

SKILL_NAME="digital-brain"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Digital Brain Installer${NC}"
echo "========================"
echo ""

# Detect installation type
echo "Where would you like to install Digital Brain?"
echo ""
echo "1) User-wide (recommended) - ~/.claude/skills/"
echo "2) Current project only   - ./.claude/skills/"
echo "3) Custom location"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        TARGET_DIR="$HOME/.claude/skills/$SKILL_NAME"
        ;;
    2)
        TARGET_DIR="./.claude/skills/$SKILL_NAME"
        ;;
    3)
        read -p "Enter custom path: " custom_path
        # Reject paths that could escape intended directories or contain shell metacharacters.
        if [[ "$custom_path" == *".."* ]] || [[ "$custom_path" =~ [[:space:]\;\|\&\$\`\<\>] ]]; then
            echo "Invalid path: must not contain '..', spaces, or shell metacharacters."
            exit 1
        fi
        # Canonicalize so symlinks and relative components are resolved before use.
        custom_path="$(realpath --canonicalize-missing -- "$custom_path")"
        TARGET_DIR="$custom_path/$SKILL_NAME"
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Create target directory
mkdir -p "$(dirname "$TARGET_DIR")"

# Check if already exists
if [ -d "$TARGET_DIR" ]; then
    read -p "Directory exists. Overwrite? [y/N]: " overwrite
    if [ "$overwrite" != "y" ] && [ "$overwrite" != "Y" ]; then
        echo "Installation cancelled."
        exit 0
    fi
    rm -rf "$TARGET_DIR"
fi

# Copy files
echo ""
echo "Installing to: $TARGET_DIR"
cp -r "$BRAIN_DIR" "$TARGET_DIR"

# Remove install script from target (not needed there)
rm -f "$TARGET_DIR/scripts/install.sh"

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Navigate to your Digital Brain: cd $TARGET_DIR"
echo "2. Start with identity/voice.md - define your voice"
echo "3. Fill out identity/brand.md - your positioning"
echo "4. Add contacts to network/contacts.jsonl"
echo "5. Capture ideas in content/ideas.jsonl"
echo ""
echo "Claude Code will automatically discover the skill."
echo "Try: 'Help me write a post in my voice'"
echo ""
