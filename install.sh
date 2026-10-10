#!/usr/bin/env bash
# waytrans installer script
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
LIB_DIR="$PREFIX/lib/waytrans"

echo "=== Installing waytrans ==="

# Check basic command-line dependencies
missing=()
for cmd in grim slurp tesseract trans wl-copy; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        missing+=("$cmd")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    echo "⚠️ Warning: The following external tools are not currently installed:"
    for m in "${missing[@]}"; do
        echo "   - $m"
    done
    echo ""
    echo "Please install them via your distribution package manager:"
    echo "  Arch/CachyOS: sudo pacman -S grim slurp tesseract translate-shell wl-clipboard gtk-layer-shell"
    echo "  Fedora:       sudo dnf install grim slurp tesseract translate-shell wl-clipboard gtk-layer-shell"
    echo "  Debian/Ubuntu:sudo apt install grim slurp tesseract-ocr translate-shell wl-clipboard libgtk-layer-shell0"
    echo ""
fi

# Create target directories
mkdir -p "$BIN_DIR"
mkdir -p "$LIB_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy python package
cp -r "$SCRIPT_DIR/waytrans" "$LIB_DIR/"

# Install wrapper executable
cat << 'EOF' > "$BIN_DIR/waytrans"
#!/usr/bin/env python3
import sys
import os

lib_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/lib/waytrans"
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from waytrans.cli import main

if __name__ == "__main__":
    main()
EOF

chmod +x "$BIN_DIR/waytrans"

echo "✓ Installed waytrans executable to $BIN_DIR/waytrans"

# Ensure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "ℹ Note: Make sure $BIN_DIR is added to your PATH in your shell config (.bashrc / .zshrc / config.fish)."
fi

# Ask or prompt to download Japanese OCR models
read -rp "Would you like to download high-accuracy Japanese OCR models now? [Y/n]: " setup_choice || setup_choice="y"
if [[ "$setup_choice" =~ ^[Yy]?$ ]]; then
    "$BIN_DIR/waytrans" --setup-models
fi

echo ""
echo "=== Installation Finished! ==="
echo "You can now bind 'waytrans' to a shortcut in your Wayland compositor:"
echo ""
echo "Hyprland (~/.config/hypr/hyprland.conf or custom/keybinds.lua):"
echo "  bind = SUPER_ALT, J, exec, waytrans -s ja -t en"
echo ""
echo "Sway (~/.config/sway/config):"
echo "  bindsym \$mod+Mod1+j exec waytrans -s ja -t en"
echo ""
