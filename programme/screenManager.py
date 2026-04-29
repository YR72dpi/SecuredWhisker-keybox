import os
import logging
import threading
import time
from PIL import Image, ImageDraw, ImageFont

# ─── Paths ────────────────────────────────────────────────────────────────────

_FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "font", "Font.ttc"
)
_PIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "pics"
)

# ─── Refresh throttle ─────────────────────────────────────────────────────────
# e-Paper partial refresh requires ≥ 600 ms between two consecutive updates.
# Calling faster causes text ghosting and overlap.

_MIN_REFRESH_INTERVAL = 0.6   # seconds
_last_refresh_time    = 0.0
_refresh_lock         = threading.Lock()


def _acquire_refresh_slot(blocking: bool = False, hold_extra: float = 0.0) -> bool:
    """Claim the next refresh slot.

    Args:
        blocking:   If True, spin-wait until the display is ready.
                    Only call from a dedicated thread — never from asyncio.
        hold_extra: Extra seconds to delay future refreshes after this one.
                    Useful for screens the user needs time to read.

    Returns:
        True if the slot was claimed, False if not ready and blocking=False.
    """
    global _last_refresh_time
    while True:
        with _refresh_lock:
            if time.monotonic() - _last_refresh_time >= _MIN_REFRESH_INTERVAL:
                _last_refresh_time = time.monotonic() + hold_extra
                return True
        if not blocking:
            return False
        time.sleep(0.05)  # wait outside the lock to let other threads through


# ─── Low-level helpers ────────────────────────────────────────────────────────

def _send_partial(epd, image: Image.Image) -> None:
    """Push an image to the display via the official partial-update sequence.

    Uses displayPartial_Wait() which:
      - does a soft SPI reset so partial-update registers are correctly set
      - writes the full framebuffer to RAM
      - calls TurnOnDisplayPart_Wait(), which waits for the BUSY pin before
        returning — preventing the "invisible screen" caused by back-to-back
        SPI commands while the display is still refreshing.
    """
    epd.displayPartial_Wait(epd.getbuffer(image))


def _blank_image(epd) -> Image.Image:
    """Return a white (blank) image sized for this display."""
    return Image.new("1", (epd.height, epd.width), 255)


# ─── Public API ───────────────────────────────────────────────────────────────

def clear(epd) -> None:
    """Erase the screen (white) using the partial-update sequence."""
    _send_partial(epd, _blank_image(epd))


def clear_and_sleep(epd) -> None:
    """Show the logo image, then put the display into sleep mode."""
    clear(epd)
    time.sleep(1)
    logo = Image.open(os.path.join(_PIC_DIR, "logo.bmp"))
    _send_partial(epd, logo)
    epd.sleep()


def print_lines(
    epd,
    lines,
    *,
    x: int = 5,
    y: int = 5,
    font_size: int = 15,
    line_spacing: int = 3,
    force: bool = False,
    hold_extra: float = 0.0,
) -> bool:
    """Render one or more lines of text on the display.

    Each call sends a complete white framebuffer with text to the e-Paper via
    displayPartial_Wait(), which waits for the BUSY pin before returning.
    No separate clear step is needed.

    Args:
        epd:          e-Paper driver instance.
        lines:        Sequence of strings to display (one per line).
        x, y:         Top-left corner of the text block, in pixels.
        font_size:    Font size in points.
        line_spacing: Extra vertical pixels between lines.
        force:        If True, spin-wait until the display is ready.
                      Call only from a worker thread, never from asyncio.
                      If False (default), skip silently when still busy.
        hold_extra:   Seconds to reserve after this update (implies force=True).

    Returns:
        True if the screen was updated, False if skipped.
    """
    if not _acquire_refresh_slot(blocking=force or hold_extra > 0, hold_extra=hold_extra):
        logging.debug("print_lines: display busy, skipping update")
        return False

    # No separate clear() needed: image already has a white background.
    # A single displayPartial_Wait() call replaces the full screen content.
    image = _blank_image(epd)
    draw  = ImageDraw.Draw(image)
    font  = ImageFont.truetype(_FONT_PATH, font_size)

    try:
        line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
    except AttributeError:  # Pillow < 9.2
        line_height = font.getsize("Ay")[1]

    cursor_y = y
    for line in (lines or []):
        if cursor_y >= epd.width:
            break
        draw.text((x, cursor_y), str(line) if line is not None else "", font=font, fill=0)
        cursor_y += line_height + line_spacing

    _send_partial(epd, image)
    logging.info("print_lines: rendered %d line(s)", len(lines) if lines else 0)
    return True