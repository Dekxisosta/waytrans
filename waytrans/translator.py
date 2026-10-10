"""
Translation module using translate-shell or fallback services.
"""

import shutil
import subprocess
from typing import Optional


class TranslationError(Exception):
    """Raised when translation operations fail."""
    pass


def check_translator_dependencies() -> None:
    """Verify that translate-shell (trans) is installed."""
    if not shutil.which("trans"):
        raise TranslationError(
            "translate-shell ('trans') is not installed. Please install it:\n"
            "  Arch/CachyOS: sudo pacman -S translate-shell\n"
            "  Fedora:       sudo dnf install translate-shell\n"
            "  Debian/Ubuntu:sudo apt install translate-shell"
        )


def translate_text(
    text: str,
    source_lang: str = "ja",
    target_lang: str = "en"
) -> str:
    """
    Translates input text from source_lang to target_lang using translate-shell.
    """
    if not text.strip():
        return ""

    check_translator_dependencies()

    cmd = [
        "trans",
        "-brief",
        "-no-ansi",
        f"{source_lang}:{target_lang}",
        text
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
    except Exception as e:
        raise TranslationError(f"Failed to execute translate-shell: {e}")

    if proc.returncode != 0:
        err = proc.stderr.strip() or "Unknown error"
        raise TranslationError(f"Translation failed: {err}")

    result = proc.stdout.strip()
    return result
