"""
Wayland Layer-Shell On-Screen Overlay for in-place text translation.
"""

import shutil
import subprocess
import sys
from typing import Optional


def notify_fallback(source_text: str, translated_text: str, title: str = "Translation") -> None:
    """Fallback desktop notification using notify-send."""
    if shutil.which("notify-send"):
        subprocess.run(
            [
                "notify-send",
                "-a", "waytrans",
                "-i", "accessories-character-map",
                title,
                f"{source_text}\n➔ {translated_text}"
            ],
            check=False
        )
    else:
        print(f"\n[{title}]\nSource:     {source_text}\nTranslated: {translated_text}")


def has_layer_shell_support() -> bool:
    """Check if PyGObject with Gtk 3.0 and GtkLayerShell is installed."""
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        gi.require_version('Gdk', '3.0')
        gi.require_version('GtkLayerShell', '0.1')
        from gi.repository import Gtk, Gdk, GtkLayerShell
        return True
    except (ValueError, ImportError):
        return False


def display_overlay(
    x: int,
    y: int,
    w: int,
    h: int,
    source_text: str,
    translated_text: str,
    timeout_ms: int = 10000,
    border_color: str = "#89b4fa",
    bg_color: str = "rgba(17, 17, 27, 0.94)"
) -> None:
    """
    Renders an in-place Wayland overlay window anchored directly over the
    selection coordinates (x, y) with width w and height h.
    """
    if not has_layer_shell_support():
        notify_fallback(source_text, translated_text)
        return

    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import Gtk, Gdk, GtkLayerShell, GLib

    Gtk.init()

    display = Gdk.Display.get_default()
    if not display:
        notify_fallback(source_text, translated_text)
        return

    # Multi-monitor coordinate detection
    monitor = display.get_monitor_at_point(x, y)
    geom = monitor.get_geometry()
    local_x = max(0, x - geom.x)
    local_y = max(0, y - geom.y)

    window = Gtk.Window()
    GtkLayerShell.init_for_window(window)
    GtkLayerShell.set_monitor(window, monitor)
    GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
    GtkLayerShell.set_namespace(window, "waytrans-overlay")

    # Anchor to top-left of the target monitor
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.TOP, True)
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.LEFT, True)
    GtkLayerShell.set_margin(window, GtkLayerShell.Edge.LEFT, local_x)
    GtkLayerShell.set_margin(window, GtkLayerShell.Edge.TOP, local_y)

    # Enable keyboard focus for fast Esc/Space dismissal
    GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.ON_DEMAND)

    # Enable true transparency
    screen = window.get_screen()
    visual = screen.get_rgba_visual()
    if visual:
        window.set_visual(visual)

    # Modern Catppuccin-styled CSS
    css = f"""
    window {{
        background-color: {bg_color};
        border: 2px solid {border_color};
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.65);
    }}
    .container {{
        padding: 6px 12px;
    }}
    .translated-label {{
        color: #cdd6f4;
        font-size: 15px;
        font-weight: 700;
        letter-spacing: 0.2px;
    }}
    .source-label {{
        color: #a6adc8;
        font-size: 11px;
        font-weight: 400;
        margin-top: 3px;
    }}
    """
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(css.encode("utf-8"))
    Gtk.StyleContext.add_provider_for_screen(
        screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    box.get_style_context().add_class("container")

    # Minimum width to cover the selected region if requested
    if w > 0:
        box.set_size_request(min(w, 850), -1)

    # Main translated text label
    trans_label = Gtk.Label()
    trans_label.set_text(translated_text)
    trans_label.set_line_wrap(True)
    trans_label.set_max_width_chars(65)
    trans_label.set_xalign(0.0)
    trans_label.get_style_context().add_class("translated-label")
    box.pack_start(trans_label, False, False, 0)

    # Source original text sub-label
    if source_text:
        src_label = Gtk.Label()
        src_label.set_text(source_text)
        src_label.set_line_wrap(True)
        src_label.set_max_width_chars(70)
        src_label.set_xalign(0.0)
        src_label.get_style_context().add_class("source-label")
        box.pack_start(src_label, False, False, 0)

    window.add(box)

    # Dismiss on click or any keypress
    window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.KEY_PRESS_MASK)
    window.connect("button-press-event", lambda w, e: Gtk.main_quit())
    window.connect("key-press-event", lambda w, e: Gtk.main_quit())

    # Optional auto-close timer (0 disables auto-close)
    if timeout_ms > 0:
        GLib.timeout_add(timeout_ms, Gtk.main_quit)

    window.show_all()
    Gtk.main()
