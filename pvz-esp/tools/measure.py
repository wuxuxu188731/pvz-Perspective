"""Zoomed measurement: crosshair at imgX/imgY plus hitbox, to calibrate sprite extents."""
import os
import struct
import subprocess

from PIL import Image, ImageDraw, ImageFont

import pvzlib as P

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOT = os.path.join(ROOT, "shots", "zoom_base.png")
OUT = os.path.join(ROOT, "shots", "zoom.png")

STRIDE = 0x204


def shot():
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", os.path.join(HERE, "shot.ps1"), "-Out", SHOT],
                   check=True, stdout=subprocess.DEVNULL)


def zombies():
    p = P.Proc(P.find_pid())
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
        row = struct.unpack_from("<i", d, 0x1C)[0]
        typ = struct.unpack_from("<i", d, 0x24)[0]
        hx, hy, hw, hh = struct.unpack_from("<4i", d, 0x8C)
        out.append(dict(ix=ix, iy=iy, row=row, typ=typ, hx=hx, hy=hy, hw=hw, hh=hh))
    p.close()
    return out


def main():
    shot()
    zs = zombies()
    if not zs:
        print("no zombies")
        return
    # pick the right-most zombie (least clutter)
    z = max(zs, key=lambda t: t["ix"])
    print("target", z)
    im = Image.open(SHOT).convert("RGB")
    dr = ImageDraw.Draw(im)
    ix, iy = z["ix"], z["iy"]
    # vertical guide at imgX (magenta) and at imgX+hit.w (cyan)
    dr.line([(ix, 0), (ix, 599)], fill=(255, 0, 255), width=1)
    dr.line([(ix + z["hx"], 0), (ix + z["hx"], 599)], fill=(0, 255, 255), width=1)
    dr.line([(ix + z["hx"] + z["hw"], 0), (ix + z["hx"] + z["hw"], 599)], fill=(0, 128, 255), width=1)
    # horizontal guide at imgY (yellow) and imgY+hit.h (orange)
    dr.line([(0, iy), (879, iy)], fill=(255, 255, 0), width=1)
    dr.line([(0, iy + z["hh"]), (879, iy + z["hh"])], fill=(255, 128, 0), width=1)
    dr.rectangle([ix + z["hx"], iy + z["hy"], ix + z["hx"] + z["hw"], iy + z["hy"] + z["hh"]],
                 outline=(255, 0, 0), width=1)

    l, t = max(0, ix - 90), max(0, iy - 100)
    r, b = min(880, ix + 170), min(600, iy + 190)
    crop = im.crop((l, t, r, b)).resize(((r - l) * 3, (b - t) * 3), Image.NEAREST)
    crop.save(OUT)
    print("crop box", (l, t, r, b), "->", OUT)
    print("imgX=%d imgY=%d hit=(%d,%d,%d,%d) row=%d typ=%d"
          % (ix, iy, z["hx"], z["hy"], z["hw"], z["hh"], z["row"], z["typ"]))


if __name__ == "__main__":
    main()
