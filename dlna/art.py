from __future__ import annotations

from io import BytesIO

from PIL import Image
from rich.text import Text


def to_ansi(data: bytes, width: int = 44) -> Text:
    """Decode an image into a colored Rich renderable.

    Each character cell is a '▀' (upper half block): its foreground colour is
    the top pixel, its background the bottom pixel. That packs two pixel rows
    per text row, doubling vertical resolution at native terminal colour.
    """
    img = Image.open(BytesIO(data)).convert("RGB")
    w, h = img.size
    cell_h = max(1, round(width * h / w * 0.5))
    px = img.resize((width, cell_h * 2)).load()
    text = Text()
    for cy in range(cell_h):
        for x in range(width):
            tr, tg, tb = px[x, cy * 2]
            br, bg, bb = px[x, cy * 2 + 1]
            text.append("▀", style=f"#{tr:02x}{tg:02x}{tb:02x} on #{br:02x}{bg:02x}{bb:02x}")
        if cy != cell_h - 1:
            text.append("\n")
    return text


if __name__ == "__main__":
    # ponytail: self-check — black left pixel, white right pixel -> the first
    # cell's foreground is black, the last cell's is white.
    img = Image.new("RGB", (2, 2))
    img.putpixel((0, 0), (0, 0, 0))
    img.putpixel((0, 1), (0, 0, 0))
    img.putpixel((1, 0), (255, 255, 255))
    img.putpixel((1, 1), (255, 255, 255))
    buf = BytesIO()
    img.save(buf, "PNG")
    art = to_ansi(buf.getvalue(), width=2)
    styles = [s.style for s in art.spans]
    assert "#000000" in str(styles[0]) and "#ffffff" in str(styles[-1]), styles
    print("ok")
