"""Ruler calibration: magenta=imgX, cyan=imgX+40, blue=imgX+80, 4x zoom."""
import os
import struct

from PIL import ImageDraw

import nav
import pvzlib as P
import screen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "shots", "zoom3.png")
STRIDE = 0x204


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
    if not rows:
        print("no zombies")
        return
    cand = [z for z in rows if z[3] >= 2] or rows
    z = max(cand, key=lambda t: t[1])
    i, ix, iy, row, typ, hx, hy, hw, hh = z
    print("target slot", i, "imgX", ix, "imgY", iy, "row", row, "typ", typ)
    dr = ImageDraw.Draw(img)
    for dx, col in ((0, (255, 0, 255)), (40, (0, 255, 255)), (80, (0, 128, 255)), (-20, (255, 0, 0))):
        if 0 <= ix + dx < 880:
            dr.line([(ix + dx, 0), (ix + dx, 599)], fill=col, width=1)
    for dy, col in ((0, (255, 255, 0)), (115, (255, 128, 0))):
        if 0 <= iy + dy < 600:
            dr.line([(0, iy + dy), (879, iy + dy)], fill=col, width=1)
    l = max(0, ix - 30)
    t = max(0, iy - 40)
    r = min(880, ix + 170)
    b = min(600, iy + 150)
    img.crop((l, t, r, b)).resize(((r - l) * 4, (b - t) * 4), 0).save(OUT)
    print("crop origin", (l, t), "scale 4  ->", OUT)


if __name__ == "__main__":
    main()
