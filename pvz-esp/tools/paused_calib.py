"""While the game is paused: measure zombie sprite bbox precisely (static scene)."""
import os
import struct

import numpy as np
from PIL import ImageDraw

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


def bbox_of(a, z, pad_l=40, pad_r=170, pad_t=70, pad_b=140):
    ix, iy = z["ix"], z["iy"]
    x0, x1 = ix - pad_l, ix + pad_r
    y0, y1 = iy - pad_t, iy + pad_b
    x0 = max(0, x0); y0 = max(0, y0)
    x1 = min(880, x1); y1 = min(600, y1)
    if x1 - x0 < 40 or y1 - y0 < 40:
        return None
    win = a[y0:y1, x0:x1]
    r = win[:, :, 0].astype(np.int32)
    g = win[:, :, 1].astype(np.int32)
    b = win[:, :, 2].astype(np.int32)
    green = (g > r + 30) & (g > b + 30)
    gfrac = float(green.mean())
    # zombie pixels: not green, and not the bright sidewalk/white
    dark = (r + g + b) < 430
    mask = (~green) & dark
    colc = mask.sum(axis=0)
    rowc = mask.sum(axis=1)
    cols = np.where(colc >= 8)[0]
    rws = np.where(rowc >= 8)[0]
    if len(cols) < 8 or len(rws) < 8:
        return None
    return dict(
        left=int(cols[0] + x0) - ix, right=int(cols[-1] + x0) - ix,
        top=int(rws[0] + y0) - iy, bottom=int(rws[-1] + y0) - iy,
        gfrac=gfrac, w=int(cols[-1] - cols[0]), h=int(rws[-1] - rws[0]))


def main():
    pid = P.find_pid()
    hwnd = nav.main_window(pid)
    p = P.Proc(pid)
    img, ok = screen.grab_window_client(hwnd)
    zs = read_zombies(p)
    p.close()
    a = np.asarray(img, dtype=np.int16)
    print("printwindow", ok, "zombies", len(zs))
    if not zs:
        print("no zombies - cannot calibrate")
        return

    results = []
    for z in zs:
        bb = bbox_of(a, z)
        tag = "big" if z["hw"] > 100 else "   "
        if bb is None:
            print("slot %2d typ %2d img(%3d,%3d) %s -> unmeasurable" % (z["slot"], z["typ"], z["ix"], z["iy"], tag))
            continue
        print("slot %2d typ %2d img(%3d,%3d) %s -> L%+4d R%+4d T%+4d B%+4d w%3d h%3d green%.2f"
              % (z["slot"], z["typ"], z["ix"], z["iy"], tag, bb["left"], bb["right"],
                 bb["top"], bb["bottom"], bb["w"], bb["h"], bb["gfrac"]))
        if z["hw"] <= 100 and bb["gfrac"] > 0.45 and 60 <= bb["w"] <= 130 and 90 <= bb["h"] <= 190:
            results.append(bb)

    if not results:
        print("\nno clean measurement")
        return

    med = {k: float(np.median([r[k] for r in results])) for k in ("left", "right", "top", "bottom", "w", "h")}
    print("\n=== median over %d clean zombies ===" % len(results))
    print("L %+.1f  R %+.1f  T %+.1f  B %+.1f   w %.1f  h %.1f"
          % (med["left"], med["right"], med["top"], med["bottom"], med["w"], med["h"]))
    print("--> box = (imgX %+.0f, imgY %+.0f)  size %.0f x %.0f"
          % (med["left"], med["top"], med["w"], med["h"]))
    print("--> 相对 hitbox(36,0,42,115): dx_left %+.0f  dw %+.0f  dy_top %+.0f  dh %+.0f"
          % (med["left"] - 36, med["w"] - 42, med["top"] - 0, med["h"] - 115))

    dr = ImageDraw.Draw(img)
    for r in results:
        pass
    dr.rectangle([0, 0, 10, 10], fill=(255, 255, 255))
    img.save(os.path.join(ROOT, "shots", "18_paused.png"))
    print("saved shots/18_paused.png")


if __name__ == "__main__":
    main()
