"""Wait for a lone first zombie, then capture a clean calibration image."""
import os
import struct
import time

from PIL import ImageDraw, ImageFont

import nav
import pvzlib as P
import screen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STRIDE = 0x204

SCENE_ZOMBIES_WON = 3


def state(p):
    lawn = p.u32(0x6A9EC0)
    if lawn == 0:
        return None
    scene = p.i32(lawn + 0x7FC)
    board = p.u32(lawn + 0x768)
    z = []
    if board:
        zb = p.u32(board + 0x90)
        cap = p.u32(board + 0x94)
        live = p.u32(board + 0xA0)
        if 0 < zb and 0 < cap <= 200:
            for i in range(cap):
                try:
                    d = p.read(zb + i * STRIDE, 0x120)
                except OSError:
                    break
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
                z.append((i, ix, iy, typ, hx, hy, hw, hh))
    else:
        live = 0
    return dict(lawn=lawn, scene=scene, board=board, zombies=z, live=live)


def main():
    pid = P.find_pid()
    p = P.Proc(pid)
    hwnd = nav.main_window(pid)
    t0 = time.time()
    clicked = False
    while time.time() - t0 < 150:
        st = state(p)
        if st is None:
            time.sleep(1)
            continue
        if st["scene"] == SCENE_ZOMBIES_WON:
            print("scene=won -> click retry")
            nav.click(440, 366)
            clicked = True
            time.sleep(4)
            continue
        if st["scene"] == 2 and st["live"] >= 1:
            zs = st["zombies"]
            if len(zs) == 1:
                ix = zs[0][1]
                if 120 < ix < 760:
                    print("lone zombie at", ix, "- capturing")
                    break
        time.sleep(0.4)
    else:
        print("timeout; last state", state(p))
        return

    img, ok = screen.grab_window_client(hwnd)
    st = state(p)
    p.close()
    if not st["zombies"]:
        print("no zombie at capture")
        return
    i, ix, iy, typ, hx, hy, hw, hh = st["zombies"][0]
    print("capture zombie", i, ix, iy, typ, hx, hy, hw, hh)
    dr = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 12)
    dr.rectangle([ix - 5, iy - 5, ix + 5, iy + 5], fill=(255, 0, 255))
    dr.rectangle([ix + hx + hw - 5, iy + hy + hh - 5, ix + hx + hw + 5, iy + hy + hh + 5], fill=(0, 255, 255))
    dr.rectangle([ix + hx - 5, iy + hy - 5, ix + hx + 5, iy + hy + 5], fill=(255, 255, 0))
    for name, col, dxl, dw, dyt, dh in (
            ("A", (0, 255, 96), -10, 21, -6, 10),
            ("B", (0, 255, 255), 0, 30, -14, 16),
            ("C", (255, 0, 255), -6, 50, -14, 16),
            ("D", (255, 160, 0), -10, 45, -24, 30)):
        x, y = ix + hx + dxl, iy + hy + dyt
        dr.rectangle([x, y, x + hw + dw, y + hh + dh], outline=col, width=1)
    dr.text((ix - 20, iy - 45), "imgX=%d imgY=%d" % (ix, iy), font=font, fill=(255, 0, 255))
    img.save(os.path.join(ROOT, "shots", "17_solo.png"))
    l, t = max(0, ix - 40), max(0, iy - 60)
    r, b = min(880, ix + 200), min(600, iy + 160)
    img.crop((l, t, r, b)).resize(((r - l) * 4, (b - t) * 4), 0).save(
        os.path.join(ROOT, "shots", "17_solo_zoom.png"))
    print("saved 17_solo.png / 17_solo_zoom.png crop", (l, t, r, b))


if __name__ == "__main__":
    main()
