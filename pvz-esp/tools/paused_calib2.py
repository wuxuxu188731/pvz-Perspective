"""Precise static-scene measurement with contiguous-run selection."""
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
    out = []
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
        out.append(dict(slot=i, ix=ix, iy=iy, typ=typ, hx=hx, hy=hy, hw=hw, hh=hh, hp=hp))
    return out


def runs(idx):
    if len(idx) == 0:
        return []
    out = []
    s = p = idx[0]
    for v in idx[1:]:
        if v == p + 1:
            p = v
        else:
            out.append((s, p))
            s = p = v
    out.append((s, p))
    return out


def main():
    pid = P.find_pid()
    hwnd = nav.main_window(pid)
    p = P.Proc(pid)
    img, ok = screen.grab_window_client(hwnd)
    zs = read_zombies(p)
    p.close()
    a = np.asarray(img, dtype=np.int16)
    print("printwindow", ok, "zombies", len(zs))

    res = []
    for z in zs:
        ix, iy = z["ix"], z["iy"]
        x0, x1 = max(0, ix - 30), min(880, ix + 170)
        y0, y1 = max(0, iy - 60), min(600, iy + 122)
        win = a[y0:y1, x0:x1]
        r = win[:, :, 0].astype(np.int32)
        g = win[:, :, 1].astype(np.int32)
        b = win[:, :, 2].astype(np.int32)
        green = (g > r + 30) & (g > b + 30)
        mask = (~green) & ((r + g + b) < 480)
        colc = mask.sum(axis=0)
        rowc = mask.sum(axis=1)
        crs = runs(np.where(colc >= 6)[0])
        rrs = runs(np.where(rowc >= 10)[0])
        if not crs or not rrs:
            print("slot %2d typ %2d img(%3d,%3d) unmeasurable" % (z["slot"], z["typ"], ix, iy))
            continue
        cs, ce = max(crs, key=lambda t: t[1] - t[0])
        rs, re = max(rrs, key=lambda t: t[1] - t[0])
        L, R = cs + x0 - ix, ce + x0 - ix
        T, B = rs + y0 - iy, re + y0 - iy
        w = R - L
        h = B - T
        print("slot %2d typ %2d img(%3d,%3d) hit(%d,%d,%d,%d) -> L%+4d R%+4d T%+4d B%+4d  w%3d h%3d"
              % (z["slot"], z["typ"], ix, iy, z["hx"], z["hy"], z["hw"], z["hh"], L, R, T, B, w, h))
        if z["hw"] <= 100 and 60 <= w <= 120 and 100 <= h <= 160:
            res.append((L, R, T, B, w, h))

    if len(res) >= 1:
        arr = np.array(res, dtype=float)
        med = np.median(arr, axis=0)
        print("\n=== median over %d normal zombies ===" % len(res))
        print("L %+.1f R %+.1f T %+.1f B %+.1f  w %.1f h %.1f"
              % (med[0], med[1], med[2], med[3], med[4], med[5]))
        print("=== vs hitbox(36,0,42,115): dx %+.0f  dw %+.0f  dy %+.0f  dh %+.0f"
              % (med[0] - 36, med[4] - 42, med[2], med[5] - 115))
        print("=== suggested: bx=imgX%+d, by=imgY%+d, bw=%d, bh=%d"
              % (round(med[0]) - 36, round(med[2]), round(med[4]), round(med[5])))


if __name__ == "__main__":
    main()
