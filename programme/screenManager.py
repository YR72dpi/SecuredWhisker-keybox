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

# Last buffer sent to the display.  Used as the 0x26 "old frame" reference so
# the SSD1680 XOR logic correctly clears pixels from the previous frame.
# Initialised to all-white to match the post-Clear(0xFF) hardware state.
_prev_buf: bytearray | None = None


def _send_partial(epd, image: Image.Image) -> None:
    """Push an image to the display using partial-update (no 010101 flash).

    The SSD1680 XOR-compares RAM 0x26 (old frame) and RAM 0x24 (new frame).
    Only pixels where XOR != 0 are refreshed:
      - Pixel was black, now white : XOR = 0xFF → driven white  (old text erased) ✓
      - Pixel was white, now black : XOR = 0xFF → driven black  (new text drawn)  ✓
      - Unchanged pixels           : XOR = 0x00 → not re-driven (stays as-is)     ✓

    0x26 is set to the ACTUAL previous frame (_prev_buf) so old text is cleared
    before new text is drawn.  Using a static all-white baseline caused old
    black pixels (previous text) to never be erased — producing overlap.
    """
    global _prev_buf

    buf = epd.getbuffer(image)
    linewidth = (epd.width // 8) if epd.width % 8 == 0 else (epd.width // 8 + 1)
    white = bytearray([0xFF] * (linewidth * epd.height))

    # Use the real previous frame as old-frame reference, or all-white on first call
    prev = _prev_buf if _prev_buf is not None else white

    # Small 1 ms reset pulse to re-enter partial-update register set
    from TP_lib import epdconfig
    epdconfig.digital_write(epd.reset_pin, 0)
    epdconfig.delay_ms(1)
    epdconfig.digital_write(epd.reset_pin, 1)

    epd.send_command(0x3C)   # BorderWaveform
    epd.send_data(0x80)
    epd.send_command(0x11)   # Data entry mode
    epd.send_data(0x03)
    epd.SetWindow(0, 0, epd.width - 1, epd.height - 1)

    # Write the previous frame so the controller knows what was on screen
    epd.SetCursor(0, 0)
    epd.send_command(0x26)
    epd.send_data2(prev)

    # Write the new frame
    epd.SetCursor(0, 0)
    epd.send_command(0x24)
    epd.send_data2(buf)

    epd.TurnOnDisplayPart_Wait()   # fast LUT, no 010101 flash

    # Remember this frame for the next call
    _prev_buf = bytearray(buf)


def _blank_image(epd) -> Image.Image:
    """Return a white (blank) image sized for this display."""
    return Image.new("1", (epd.height, epd.width), 255)


# ─── Public API ───────────────────────────────────────────────────────────────

def clear(epd) -> None:
    """Erase the screen (white) without flash."""
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

    # Draw text on a greyscale image so Pillow uses proper anti-aliasing,
    # then threshold to pure black/white before sending to the display.
    image = Image.new("L", (epd.height, epd.width), 255)  # greyscale, white
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

    # Convert greyscale → 1-bit without dithering: any pixel darker than 200
    # becomes solid black, everything else is white.  This avoids dithering
    # noise (which looks grey/ghosted on e-ink) while preserving text quality.
    image = image.point(lambda px: 0 if px < 200 else 255, "1")

    _send_partial(epd, image)
    logging.info("print_lines: rendered %d line(s)", len(lines) if lines else 0)
    return True