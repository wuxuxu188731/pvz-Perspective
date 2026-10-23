"""Draw several candidate box offsets around every live zombie, full frame + zoomed crop."""
import os
import struct

from PIL import ImageDraw, ImageFont

import nav
import pvzlib as P
import screen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_FULL = os.path.join(ROOT, "shots", "cand_full.png")
OUT_ZOOM = os.path.join(ROOT, "shots", "cand_zoom.png")
STRIDE = 0x204

CANDS = [
    ("A", (0, 255, 96), -10, 21, -6, 10),
    ("B", (0, 255, 255), 5, 35, -10, 16),
    ("C", (255, 0, 255), 20, 50, -14, 22),
    ("D", (255, 160, 0), -2, 45, -20, 30),
]


def read_zombies(p):
    lawn = p.u32(0x6A9EC0)
    board = p.u32(lawn + 0x768)
    zb = p.u32(board + 0x90)
    cap = p.u32(board + 0x94)
    rows = []
    for i in range(cap):
        d = p.read(zb + i * STRIDE, 0x120)
        if struct.unpack_from("<I", d, 0)[0] != lawn:
            continue
        if struct.unpack_from("<i", d, 0xEC)[0]:
            continue
        hp = struct.unpack_from("<i", d, 0xC8)[0]
        if hp <= 0:
            continue
        ix, iy = struct.unpack_from("<ii", d, 8)
        row = struct.unpack_from("<i", d, 0x1C)[0]
        typ = struct.unpack_from("<i", d, 0x24)[0]
        hx, hy, hw, hh = struct.unpack_from("<4i", d, 0x8C)
        rows.append((i, ix, iy, row, typ, hx, hy, hw, hh))
    return rows


def main():
    pid = P.find_pid()
    hwnd = nav.main_window(pid)
    p = P.Proc(pid)
    img, ok = screen.grab_window_client(hwnd)
    rows = read_zombies(p)
    p.close()
    print("zombies", len(rows))
    if not rows:
        img.save(OUT_FULL)
        return
    dr = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 11)
    for (i, ix, iy, row, typ, hx, hy, hw, hh) in rows:
        for name, col, dxl, dw, dyt, dh in CANDS:
            x = ix + hx + dxl
            y = iy + hy + dyt
            w = hw + dw
            h = hh + dh
            dr.rectangle([x, y, x + w, y + h], outline=col, width=1)
        dr.text((ix + hx - 10, iy + hy - 26), "T%d" % typ, font=font, fill=(255, 255, 0))
    img.save(OUT_FULL)

    # zoomed crop around the right-most zombie
    z = max(rows, key=lambda t: t[1])
    i, ix, iy, row, typ, hx, hy, hw, hh = z
    l, t = max(0, ix - 40), max(0, iy - 60)
    r, b = min(880, ix + 200), min(600, iy + 160)
    img.crop((l, t, r, b)).resize(((r - l) * 3, (b - t) * 3), 0).save(OUT_ZOOM)
    print("target", z)
    print("saved", OUT_FULL, OUT_ZOOM)


if __name__ == "__main__":
    main()
