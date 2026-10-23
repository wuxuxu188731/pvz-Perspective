"""Automated sprite bbox measurement on grass, median over many zombies."""
import os
import struct

import numpy as np

import nav
import pvzlib as P
import screen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
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
        typ = struct.unpack_from("<i", d, 0x24)[0]
        hx, hy, hw, hh = struct.unpack_from("<4i", d, 0x8C)
        rows.append((i, ix, iy, typ, hx, hy, hw, hh))
    return rows


def main():
    pid = P.find_pid()
    hwnd = nav.main_window(pid)
    p = P.Proc(pid)
    img, ok = screen.grab_window_client(hwnd)
    rows = read_zombies(p)
    p.close()
    a = np.asarray(img, dtype=np.int16)
    print("printwindow", ok, "zombies", len(rows))

    L, R, T, B = [], [], [], []
    for (i, ix, iy, typ, hx, hy, hw, hh) in rows:
        if hw > 100:      # skip big/odd types
            continue
        x0, x1 = ix - 30, ix + 160
        y0, y1 = iy - 40, iy + 140
        if x0 < 0 or y0 < 0 or x1 > 880 or y1 > 600:
            continue
        win = a[y0:y1, x0:x1]
        r = win[:, :, 0].astype(np.int32)
        g = win[:, :, 1].astype(np.int32)
        b = win[:, :, 2].astype(np.int32)
        green = (g > r + 30) & (g > b + 30)
        if green.mean() < 0.45:
            continue   # cluttered background
        dark = (r + g + b) < 330
        mask = (~green) & dark
        colcount = mask.sum(axis=0)
        rowcount = mask.sum(axis=1)
        cols = np.where(colcount >= 10)[0]
        rws = np.where(rowcount >= 10)[0]
        if len(cols) < 10 or len(rws) < 10:
            continue
        l, rr = cols[0] + x0, cols[-1] + x0
        t, bb = rws[0] + y0, rws[-1] + y0
        print("slot %2d typ %d img(%d,%d) -> dL%+4d dR%+4d dT%+4d dB%+4d  w=%3d h=%3d green=%.2f"
              % (i, typ, ix, iy, l - ix, rr - ix, t - iy, bb - iy, rr - l, bb - t, green.mean()))
        L.append(l - ix)
        R.append(rr - ix)
        T.append(t - iy)
        B.append(bb - iy)

    if len(L) >= 3:
        print("\n=== median over %d zombies ===" % len(L))
        print("dL %+.1f   dR %+.1f   dT %+.1f   dB %+.1f   w %.1f  h %.1f"
              % (np.median(L), np.median(R), np.median(T), np.median(B),
                 np.median(R) - np.median(L), np.median(B) - np.median(T)))
        print("stdev   L %.1f R %.1f T %.1f B %.1f"
              % (np.std(L), np.std(R), np.std(T), np.std(B)))


if __name__ == "__main__":
    main()
