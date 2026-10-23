"""Offline preview: read zombie data, take a screenshot, draw the ESP overlay, save PNG."""
import os
import struct
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

import pvzlib as P

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOT = os.path.join(ROOT, "shots", "preview_base.png")
OUT = os.path.join(ROOT, "shots", "preview_overlay.png")

STRIDE = 0x204


def shot():
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", os.path.join(HERE, "shot.ps1"), "-Out", SHOT],
        check=True, stdout=subprocess.DEVNULL)


def read_state():
    pid = P.find_pid()
    if pid is None:
        raise SystemExit("game not running")
    p = P.Proc(pid)
    lawn = p.u32(0x6A9EC0)
    board = p.u32(lawn + 0x768)
    zb = p.u32(board + 0x90)
    zcap = p.u32(board + 0x94)
    zlive = p.u32(board + 0xA0)
    sun = p.i32(board + 0x5560)
    wave = p.i32(board + 0x557C)
    total_wave = p.i32(board + 0x5564)
    zombies = []
    for i in range(zcap):
        o = zb + i * STRIDE
        d = p.read(o, 0x160)
        if struct.unpack_from("<I", d, 0)[0] != lawn:
            continue
        imgx, imgy = struct.unpack_from("<ii", d, 8)
        vis = d[0x18]
        row = struct.unpack_from("<i", d, 0x1C)[0]
        typ = struct.unpack_from("<i", d, 0x24)[0]
        hp = struct.unpack_from("<i", d, 0xC8)[0]
        hpm = struct.unpack_from("<i", d, 0xCC)[0]
        a1 = struct.unpack_from("<i", d, 0xD0)[0]
        a1m = struct.unpack_from("<i", d, 0xD4)[0]
        a2 = struct.unpack_from("<i", d, 0xDC)[0]
        a2m = struct.unpack_from("<i", d, 0xE0)[0]
        died = struct.unpack_from("<i", d, 0xEC)[0]
        hx, hy, hw, hh = struct.unpack_from("<4i", d, 0x8C)
        if died or hp <= 0:
            continue
        total = max(hp, 0) + (max(a1, 0) if a1m > 0 else 0) + (max(a2, 0) if a2m > 0 else 0)
        tmax = max(hpm, 1) + (a1m if a1m > 0 else 0) + (a2m if a2m > 0 else 0)
        zombies.append(dict(slot=i, x=imgx + hx, y=imgy + hy, w=hw, h=hh,
                            row=row, typ=typ, hp=total, hpmax=tmax))
    p.close()
    return dict(sun=sun, wave=wave, twave=total_wave, zlive=zlive,
                zombies=zombies)


def main():
    shot()
    st = read_state()
    im = Image.open(SHOT).convert("RGB")
    dr = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)
    except Exception:
        font = ImageFont.load_default()

    for z in st["zombies"]:
        x, y, w, h = z["x"], z["y"], z["w"], z["h"]
        dr.rectangle([x, y, x + w, y + h], outline=(0, 255, 0), width=2)
        # hp bar
        bx, by, bw, bh = x, max(0, y - 9), max(w, 40), 5
        dr.rectangle([bx, by, bx + bw, by + bh], fill=(60, 0, 0))
        frac = max(0.0, min(1.0, z["hp"] / z["hpmax"]))
        dr.rectangle([bx, by, bx + int(bw * frac), by + bh], fill=(0, 230, 0))
        dr.text((bx, max(0, by - 15)), "Z%d %d/%d" % (z["typ"], z["hp"], z["hpmax"]),
                font=font, fill=(255, 255, 0))

    dr.text((10, 596 - 16), "sun=%d  wave=%d/%d  zombies=%d"
            % (st["sun"], st["wave"], st["twave"], st["zlive"]),
            font=font, fill=(0, 255, 255))
    im.save(OUT)
    print("zombies drawn:", len(st["zombies"]), "->", OUT)
    print("sun=%d wave=%d/%d" % (st["sun"], st["wave"], st["twave"]))


if __name__ == "__main__":
    main()
