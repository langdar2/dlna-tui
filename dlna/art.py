from __future__ import annotations

from io import BytesIO

from PIL import Image

# Dense -> sparse. A dark pixel (low luminance) maps to '@', so cover art shows
# as "ink" on a dark terminal.
_RAMP = "@%#*+=-:. "


def to_ascii(data: bytes, width: int = 44) -> str:
    """Decode an image and render it as greyscale ASCII art.

    Height is halved because terminal cells are ~twice as tall as wide.
    """
    img = Image.open(BytesIO(data)).convert("L")
    w, h = img.size
    height = max(1, round(width * h / w * 0.5))
    px = list(img.resize((width, height)).getdata())
    scale = (len(_RAMP) - 1) / 255
    rows = ["".join(_RAMP[int(px[y * width + x] * scale)] for x in range(width))
            for y in range(height)]
    return "\n".join(rows)


if __name__ == "__main__":
    # ponytail: self-check — a black left half / white right half must map to
    # the dense char on the left and the sparse (space) char on the right.
    img = Image.new("L", (2, 1))
    img.putpixel((0, 0), 0)
    img.putpixel((1, 0), 255)
    buf = BytesIO()
    img.save(buf, "PNG")
    art = to_ascii(buf.getvalue(), width=2)
    assert art[0] == "@" and art[-1] == " ", art
    print("ok:", repr(art))
