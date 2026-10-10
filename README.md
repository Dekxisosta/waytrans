# waytrans 🌐✨

> **Instant in-place screen OCR translator for Wayland desktops.**  
> Snip any foreign text (Japanese manga, games, visual novels, websites) and see the translation rendered **directly on top of the original words**.

---

## 📸 Overview

Traditional Linux OCR translation scripts typically dump translated text into a desktop notification toast in the corner of your monitor. When playing a visual novel, reading manga, or browsing Japanese media, looking away at notification bubbles breaks immersion.

`waytrans` solves this by utilizing **Wayland Layer-Shell (`GtkLayerShell`)**:
1. You drag a selection box around any text on screen.
2. `waytrans` captures and enhances the crop, extracts characters with Tesseract (with full CJK horizontal & vertical support), and translates it immediately.
3. A sleek floating overlay appears **directly over the original words** on your display.
4. Dismiss it instantly with a click or `Esc`, or let it auto-fade after a customizable timeout.
5. The translation is also automatically placed in your clipboard (`wl-copy`).

---

## ✨ Features

- 🔄 **Dynamic Live Translation (Toggle Mode)**: Simply toggle it on; it continuously watches dialogue boxes or manga panels, detects new incoming text via perceptual hashing, and dynamically updates the translation in-place!
- 🖱️ **Click-Through in Live Mode**: Allows full mouse pass-through during live mode so you can click to advance dialogue or play games without interruption.
- 🎯 **In-Place Floating Overlay**: Anchored directly to the `(X, Y)` screen coordinates where the original text was selected.
- 🖥️ **Multi-Monitor Aware**: Automatically resolves global compositor coordinates to the active monitor.
- 🇯🇵 **Optimized for Japanese & CJK**: Handles both horizontal and vertical text (`jpn+jpn_vert`), removes OCR space insertion artifacts, and supports `tessdata_best` high-accuracy models.
- ⚡ **Lightweight & Fast**: Uses native desktop Wayland protocols (`slurp`, `grim`, `gtk-layer-shell`) with zero heavyweight electron/web runtimes.
- 📋 **Automatic Clipboard Sync**: Translated text is automatically copied via `wl-copy`.
- ⌨️ **Interactive Dismissal**: Click anywhere on the snippet overlay or press `Esc` / `Space` to close it immediately.
- 🔔 **Graceful Fallback**: If running without Layer-Shell, falls back automatically to standard desktop notifications (`notify-send`).
- 🛠️ **Built-in Model Installer**: One command (`waytrans --setup-models`) fetches high-accuracy models.

---

## 📦 Requirements & Dependencies

`waytrans` relies on standard Linux Wayland and OCR utilities.

### 1. Arch Linux / CachyOS / Manjaro
```bash
sudo pacman -S grim slurp tesseract translate-shell wl-clipboard gtk-layer-shell python-gobject
```

### 2. Fedora / RHEL
```bash
sudo dnf install grim slurp tesseract translate-shell wl-clipboard gtk-layer-shell python3-gobject
```

### 3. Ubuntu / Debian
```bash
sudo apt install grim slurp tesseract-ocr translate-shell wl-clipboard libgtk-layer-shell0 python3-gi
```

*(Optional)*: `imagemagick` for automated 2x contrast pre-processing on low-resolution text.

---

## 🚀 Installation

### Option 1: Quick Install (Recommended)

Clone the repository and run the installer:

```bash
git clone https://github.com/<your-username>/waytrans.git
cd waytrans
./install.sh
```

This installs the binary to `~/.local/bin/waytrans` and prompts you to download high-accuracy Japanese OCR models.

### Option 2: Python / Pip Install

```bash
git clone https://github.com/<your-username>/waytrans.git
cd waytrans
pip install --user .
```

---

## 🎌 Setting Up Japanese Models

For accurate Japanese character recognition (especially manga, games, and vertical dialogue), download the official `tessdata_best` models:

```bash
waytrans --setup-models
```

This places `jpn.traineddata` and `jpn_vert.traineddata` into `~/.local/share/tessdata/`.

---

## ⌨️ Compositor Keybindings

Add a shortcut to your Wayland compositor configuration:

### Hyprland

In `~/.config/hypr/hyprland.conf`:
```ini
# One-shot screen translation (Super + Alt + J)
bind = SUPER_ALT, J, exec, waytrans -s ja -t en

# Dynamic Live Translation toggle (Super + Alt + L)
bind = SUPER_ALT, L, exec, waytrans --live -s ja -t en
```

Or if you use Hyprland Lua configurations (`~/.config/hypr/custom/keybinds.lua`):
```lua
hl.bind("SUPER + ALT + J", hl.dsp.exec_cmd("waytrans -s ja -t en"), { description = "Translate screen JP to EN" })
hl.bind("SUPER + ALT + L", hl.dsp.exec_cmd("waytrans --live -s ja -t en"), { description = "Toggle Live Translation" })
```

### Sway

In `~/.config/sway/config`:
```ini
bindsym $mod+Mod1+j exec waytrans -s ja -t en
bindsym $mod+Mod1+l exec waytrans --live -s ja -t en
```

### River

In `~/.config/river/init`:
```bash
riverctl map normal Super+Alt J spawn "waytrans -s ja -t en"
riverctl map normal Super+Alt L spawn "waytrans --live -s ja -t en"
```

---

## 🛠️ CLI Usage & Flags

```text
usage: waytrans [-h] [-s SOURCE] [-t TARGET] [--timeout TIMEOUT] [--psm PSM]
                [--no-overlay] [--no-clipboard] [--notify] [-l]
                [--interval INTERVAL] [--stop-live] [--setup-models] [-v]

options:
  -h, --help           Show help message and exit
  -s, --source SOURCE  Source language code (default: ja)
  -t, --target TARGET  Target language code (default: en)
  --timeout TIMEOUT    Overlay timeout in seconds (default: 10, 0 = stay until clicked)
  --psm PSM            Tesseract Page Segmentation Mode (default: 6)
  --no-overlay         Disable in-place overlay (desktop notification only)
  --no-clipboard       Disable copying translation to clipboard
  --notify             Trigger a desktop notification alongside the overlay
  -l, --live           Toggle dynamic live translation mode on or off
  --interval INTERVAL  Polling interval in seconds for live translation (default: 0.5)
  --stop-live          Stop any currently running live translation session
  --setup-models       Download high-accuracy Japanese OCR models
  -v, --version        Show version
```

### Examples

**One-shot translation:**
```bash
waytrans
```

**Toggle Live / Dynamic translation on/off:**
```bash
waytrans -l
```

Translate Chinese (Simplified) to English in live mode:
```bash
waytrans -l -s zh -t en
```

Translate German to English with a 20-second timeout:
```bash
waytrans -s de -t en --timeout 20
```

Notification-only mode (traditional toast style):
```bash
waytrans --no-overlay
```

---

## 🧠 Architecture

```text
[ User presses Hotkey ]
          │
          ▼
   [ slurp ] ───► Interactive drag selection (X, Y, W, H)
          │
          ▼
   [ grim ] ────► Screenshot cropped region
          │
          ▼
 [ ImageMagick ]► Optional 2x upscale & grayscale preprocessing
          │
          ▼
 [ Tesseract ] ─► OCR recognition (horizontal + vertical CJK cleanup)
          │
          ▼
[ translate-shell ] ► Translate source to target language
          │
          ├─────────────────────────┬─────────────────────────┐
          ▼                         ▼                         ▼
   [ wl-clipboard ]       [ GtkLayerShell Overlay ]    [ Desktop Notification ]
   (Copied to clipboard)    (Floating in-place card)     (Optional / Fallback)
```

---

## ❓ FAQ & Troubleshooting

#### Q: The overlay does not appear, only a notification shows up.
Ensure `gtk-layer-shell` and `python-gobject` (`python3-gi`) are installed on your system. `waytrans` automatically falls back to notifications if the layer-shell library cannot be loaded.

#### Q: Tesseract misreads stylized Japanese fonts or vertical text.
Run `waytrans --setup-models` to install the `tessdata_best` models. They are significantly more accurate for complex kanji and furigana than the default distro `tessdata_fast` packages.

#### Q: How do I change the overlay colors or theme?
The overlay is styled via CSS inside `waytrans/overlay.py`. You can adjust border color, background opacity, and font sizing to match your desktop rice.

---

## 📄 License

Distributed under the [MIT License](LICENSE).
