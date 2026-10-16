"""Find the iDotMatrix display and put test pictures on it.

    python3 -m dlna.idm_probe [address-or-name]

Prints every display in range, then walks through the same sequence the player
uses on a track change, pausing between steps so you can see what appears:

  1. cover with a half-full progress bar
  2. a scrolling line of text (a GIF)
  3. the cover again   <- the step that has to switch back from the GIF

Say which step first fails to show.
"""
import asyncio
import os
import sys
from io import BytesIO

from PIL import Image, ImageDraw

from .display import PixelDisplay, cover_frame, scroll_frames


def _png(img) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def main(target: str) -> int:
    from .display import import_idotmatrix
    found = await import_idotmatrix().ConnectionManager.scan()
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
    cover = cover_frame(_png(tile), 16)

    print("1. cover + progress bar (blue square, yellow disc, green bar)")
    await d._send_png(cover)
    await asyncio.sleep(4)

    print("2. scrolling text")
    await d._send_gif(scroll_frames("dlna-tui test"))
    await asyncio.sleep(8)

    print("3. cover again (should return to the blue square)")
    await d._send_png(cover)
    await asyncio.sleep(5)

    await d.close()
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else
                              os.environ.get("DLNA_TUI_IDM", ""))))
