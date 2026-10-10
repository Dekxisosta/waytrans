"""
Live dynamic screen translation module for Wayland.
Watches a selected screen region, detects text changes, and updates
an in-place click-through overlay in real time.
"""

import hashlib
import os
import signal
import subprocess
import sys
import tempfile
import time
from typing import Optional, Tuple

from waytrans.capture import capture_region, CaptureError
from waytrans.ocr import run_ocr
from waytrans.translator import translate_text
from waytrans.overlay import has_layer_shell_support, notify_fallback

PID_FILE = os.path.expanduser("~/.cache/waytrans/live.pid")


def get_pid_file() -> str:
    """Return and ensure directory for the PID file."""
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    return PID_FILE


def is_live_running() -> Optional[int]:
    """Check if a live translation daemon is currently active."""
    pid_path = get_pid_file()
    if not os.path.exists(pid_path):
        return None

    try:
        with open(pid_path, "r") as f:
            pid = int(f.read().strip())
        # Check if process is running (signal 0 doesn't kill it)
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        # Stale PID file
        if os.path.exists(pid_path):
            try:
                os.remove(pid_path)
            except OSError:
                pass
        return None


def stop_live() -> bool:
    """Stop any running live translation process."""
    pid = is_live_running()
    if not pid:
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass

    pid_path = get_pid_file()
    if os.path.exists(pid_path):
        try:
            os.remove(pid_path)
        except OSError:
            pass

    notify_fallback("Live Mode", "🛑 Live translation disabled.", title="waytrans")
    return True


def compute_image_hash(image_path: str) -> str:
    """
    Computes a fast perceptual hash (aHash) using Pillow,
    or falls back to MD5 if Pillow is unavailable.
    """
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            thumb = img.convert('L').resize((16, 16), Image.Resampling.BILINEAR)
            pixels = list(thumb.getdata())
            avg = sum(pixels) / max(len(pixels), 1)
            bits = "".join("1" if p > avg else "0" for p in pixels)
            return hex(int(bits, 2))
    except Exception:
        # Fallback to MD5 of raw file content
        hasher = hashlib.md5()
        with open(image_path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()


class LiveTranslator:
    def __init__(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        source_lang: str = "ja",
        target_lang: str = "en",
        interval_ms: int = 400,
        psm: int = 6,
        copy_clipboard: bool = True
    ):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.geometry = f"{x},{y} {w}x{h}"
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.interval_ms = interval_ms
        self.psm = psm
        self.copy_clipboard = copy_clipboard

        self.last_img_hash = ""
        self.last_text = ""
        self.tmp_img = tempfile.mktemp(suffix=".png", prefix="waytrans_live_")

        self.window = None
        self.en_label = None
        self.jp_label = None
        self.status_label = None

    def cleanup(self) -> None:
        """Clean up temporary files and PID file."""
        if os.path.exists(self.tmp_img):
            try:
                os.remove(self.tmp_img)
            except OSError:
                pass
        pid_path = get_pid_file()
        if os.path.exists(pid_path):
            try:
                os.remove(pid_path)
            except OSError:
                pass

    def setup_ui(self) -> None:
        """Initializes the GtkLayerShell overlay window."""
        import gi
        import cairo
        gi.require_version('Gtk', '3.0')
        gi.require_version('Gdk', '3.0')
        gi.require_version('GtkLayerShell', '0.1')
        from gi.repository import Gtk, Gdk, GtkLayerShell

        Gtk.init()

        display = Gdk.Display.get_default()
        monitor = display.get_monitor_at_point(self.x, self.y)
        geom = monitor.get_geometry()
        local_x = max(0, self.x - geom.x)
        local_y = max(0, self.y - geom.y)

        self.window = Gtk.Window()
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_monitor(self.window, monitor)
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self.window, "waytrans-live-overlay")

        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.LEFT, local_x)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, local_y)

        # Keyboard mode none allows full typing underneath
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)

        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)

        # CSS Styling
        css = b"""
        window {
            background-color: rgba(17, 17, 27, 0.88);
            border: 2px solid #a6e3a1;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
        }
        .container {
            padding: 6px 12px;
        }
        .live-tag {
            color: #a6e3a1;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .translated-label {
            color: #cdd6f4;
            font-size: 15px;
            font-weight: 700;
        }
        .source-label {
            color: #a6adc8;
            font-size: 11px;
            font-weight: 400;
            margin-top: 2px;
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.get_style_context().add_class("container")
        box.set_size_request(min(self.w, 850), -1)

        self.status_label = Gtk.Label(label="● LIVE TRANSLATING")
        self.status_label.set_xalign(0.0)
        self.status_label.get_style_context().add_class("live-tag")
        box.pack_start(self.status_label, False, False, 0)

        self.en_label = Gtk.Label(label="Waiting for text...")
        self.en_label.set_line_wrap(True)
        self.en_label.set_max_width_chars(65)
        self.en_label.set_xalign(0.0)
        self.en_label.get_style_context().add_class("translated-label")
        box.pack_start(self.en_label, False, False, 0)

        self.jp_label = Gtk.Label(label="")
        self.jp_label.set_line_wrap(True)
        self.jp_label.set_max_width_chars(70)
        self.jp_label.set_xalign(0.0)
        self.jp_label.get_style_context().add_class("source-label")
        box.pack_start(self.jp_label, False, False, 0)

        self.window.add(box)
        self.window.realize()

        # CRITICAL: Make the window click-through so user can interact with game/manga beneath!
        self.window.input_shape_combine_region(cairo.Region())
        self.window.show_all()

    def tick(self) -> bool:
        """Single polling cycle executed on timer."""
        from gi.repository import Gtk

        try:
            # 1. Capture watched region
            proc = subprocess.run(
                ["grim", "-g", self.geometry, self.tmp_img],
                capture_output=True,
                check=False
            )
            if proc.returncode != 0 or not os.path.exists(self.tmp_img):
                return True

            # 2. Check if screen region changed
            img_hash = compute_image_hash(self.tmp_img)
            if img_hash == self.last_img_hash:
                return True  # No visual change, skip OCR & translation

            self.last_img_hash = img_hash

            # 3. Extract text via OCR
            text = run_ocr(self.tmp_img, lang=self.source_lang, psm=self.psm)
            if text == self.last_text:
                return True  # Text content identical, do not retranslate

            self.last_text = text

            if not text:
                # Text cleared from region
                self.en_label.set_text("...")
                self.jp_label.set_text("")
                return True

            # 4. Translate newly detected text
            translated = translate_text(
                text,
                source_lang=self.source_lang,
                target_lang=self.target_lang
            )

            # 5. Update UI in-place
            self.en_label.set_text(translated)
            self.jp_label.set_text(text)

            # 6. Clipboard sync if enabled
            if self.copy_clipboard:
                subprocess.run(["wl-copy"], input=translated.encode("utf-8"), check=False)

        except Exception as e:
            print(f"Live translation tick error: {e}", file=sys.stderr)

        return True  # Keep GLib timer alive

    def run(self) -> None:
        """Starts the live monitoring loop."""
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, GLib

        # Write current PID
        with open(get_pid_file(), "w") as f:
            f.write(str(os.getpid()))

        # Register termination signal handlers
        def handle_signal(sig, frame):
            self.cleanup()
            Gtk.main_quit()
            sys.exit(0)

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        self.setup_ui()

        # Run first tick immediately, then schedule recurring checks
        self.tick()
        GLib.timeout_add(self.interval_ms, self.tick)

        try:
            Gtk.main()
        finally:
            self.cleanup()


def toggle_live(
    source_lang: str = "ja",
    target_lang: str = "en",
    interval: float = 0.5,
    psm: int = 6,
    copy_clipboard: bool = True
) -> None:
    """Toggles dynamic live translation mode on or off."""
    if is_live_running():
        stop_live()
        print("Live translation stopped.")
        return

    # Start live translation
    if not has_layer_shell_support():
        notify_fallback("Live Mode Error", "Live mode requires gtk-layer-shell.", title="waytrans")
        return

    notify_fallback("Live Mode", "Select region to watch...", title="waytrans")

    try:
        captured = capture_region(border_color="#a6e3a1", bg_color="#1e1e2e66")
    except CaptureError as e:
        print(f"Capture error: {e}", file=sys.stderr)
        return

    if not captured:
        print("Selection cancelled.")
        return

    image_path, x, y, w, h = captured
    if os.path.exists(image_path):
        try:
            os.remove(image_path)
        except OSError:
            pass

    notify_fallback(
        "Live Mode",
        f"🟢 Live translation active ({w}x{h}). Press toggle hotkey again to stop.",
        title="waytrans"
    )

    watcher = LiveTranslator(
        x=x,
        y=y,
        w=w,
        h=h,
        source_lang=source_lang,
        target_lang=target_lang,
        interval_ms=int(interval * 1000),
        psm=psm,
        copy_clipboard=copy_clipboard
    )
    watcher.run()
