"""
Screen capture utilities using Wayland grim and slurp.
"""

import os
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple


class CaptureError(Exception):
    """Raised when screen capture fails or is cancelled."""
    pass


def check_capture_dependencies() -> None:
    """Verify that grim and slurp are installed."""
    missing = [tool for tool in ("slurp", "grim") if not shutil.which(tool)]
    if missing:
        raise CaptureError(
            f"Missing required Wayland capture tools: {', '.join(missing)}. "
            "Please install them via your package manager."
        )


def capture_region(
    border_color: str = "#89b4fa",
    bg_color: str = "#1e1e2e88",
    border_width: int = 2
) -> Optional[Tuple[str, int, int, int, int]]:
    """
    Interactively prompts user to select a screen region using slurp,
    then saves the screenshot using grim.

    Returns:
        (image_path, x, y, width, height) or None if cancelled.
    """
    check_capture_dependencies()

    slurp_cmd = [
        "slurp",
        "-d",
        "-c", border_color,
        "-b", bg_color,
        "-w", str(border_width),
    ]

    try:
        proc = subprocess.run(
            slurp_cmd,
            capture_output=True,
            text=True,
            check=False
        )
    except Exception as e:
        raise CaptureError(f"Failed to run slurp: {e}")

    geometry = proc.stdout.strip()
    if not geometry or proc.returncode != 0:
        return None  # Selection was cancelled by user (e.g. Esc)

    # Geometry output format: "X,Y WxH"
    try:
        coords, dims = geometry.split(" ")
        x_str, y_str = coords.split(",")
        w_str, h_str = dims.split("x")
        x, y, w, h = int(x_str), int(y_str), int(w_str), int(h_str)
    except ValueError:
        raise CaptureError(f"Unexpected geometry format from slurp: '{geometry}'")

    # Create temporary file for screenshot
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png", prefix="waytrans_")
    os.close(tmp_fd)

    grim_cmd = ["grim", "-g", geometry, tmp_path]
    try:
        grim_proc = subprocess.run(grim_cmd, capture_output=True, check=False)
        if grim_proc.returncode != 0:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise CaptureError(f"grim failed: {grim_proc.stderr.decode().strip()}")
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise CaptureError(f"Failed to capture region with grim: {e}")

    # Optional image preprocessing if ImageMagick is available
    if shutil.which("magick"):
        try:
            subprocess.run(
                ["magick", tmp_path, "-resize", "200%", "-colorspace", "Gray", tmp_path],
                capture_output=True,
                check=False
            )
        except Exception:
            pass

    return tmp_path, x, y, w, h
