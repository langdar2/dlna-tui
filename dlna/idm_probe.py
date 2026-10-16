"""Find the iDotMatrix display and put a test picture on it.

    python3 -m dlna.idm_probe [address-or-name]

Prints every display in range, then shows a cover tile with a half-filled
progress bar and a scrolling line of text, so you can check the connection
before running the player with DLNA_TUI_IDM.
"""
import asyncio
import os
import sys

from PIL import Image, ImageDraw

from .display import PixelDisplay, cover_frame, scroll_frames


async def main(target: str) -> int:
    from idotmatrix import ConnectionManager
    found = await ConnectionManager.scan()
    print("displays in range:", found or "none")
    if not target:
        if not found:
            return 1
        target = found[0]
    d = PixelDisplay(target)
    if not await d.connect():
        print("could not connect:", d.last_error)
        return 1
    tile = Image.new("RGB", (64, 64), (30, 60, 160))
    ImageDraw.Draw(tile).ellipse((12, 12, 52, 52), fill=(240, 200, 40))
    await d._send_png(cover_frame(_png(tile), 16))
    await asyncio.sleep(3)
    await d._send_gif(scroll_frames("dlna-tui test"))
    await asyncio.sleep(6)
    await d.close()
    print("ok")
    return 0


def _png(img):
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else
                              os.environ.get("DLNA_TUI_IDM", ""))))
