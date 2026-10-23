"""Tightly-synchronised calibration: fast GDI capture + immediate memory read."""
import ctypes
import os
import struct
import subprocess
import time
from ctypes import wintypes as wt

from PIL import ImageDraw

import pvzlib as P
import screen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "shots", "zoom2.png")
STRIDE = 0x204

u32 = ctypes.WinDLL("user32", use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def client_origin(hwnd):
    pt = POINT(0, 0)
    u32.ClientToScreen(hwnd, ctypes.byref(pt))
    rc = RECT()
    u32.GetClientRect(hwnd, ctypes.byref(rc))
    return pt.x, pt.y, rc.right, rc.bottom


def zombies(p):
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
    return out


def main():
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                    "Get-Process Overlay -ErrorAction SilentlyContinue | Stop-Process -Force"],
                   check=False, stdout=subprocess.DEVNULL)
    time.sleep(0.3)
    pid = P.find_pid()
    u32.GetWindowThreadProcessId.restype = wt.DWORD
    # find the main window by enumeration
    import nav
    hwnd = nav.main_window(pid)
    ox, oy, w, h = client_origin(hwnd)
    p = P.Proc(pid)
    img, ok = screen.grab_window_client(hwnd)
    zs = zombies(p)          # read immediately after the grab
    p.close()
    print("client origin", ox, oy, "size", w, h, "printwindow_ok", ok, "zombies", len(zs))
    if not zs:
        img.save(OUT)
        print("no zombies; saved raw", OUT)
        return
    z = max(zs, key=lambda t: t["ix"])
    print("target", z)
    dr = ImageDraw.Draw(img)
    ix, iy = z["ix"], z["iy"]
    dr.line([(ix, 0), (ix, h - 1)], fill=(255, 0, 255), width=1)
    dr.line([(ix + z["hx"], 0), (ix + z["hx"], h - 1)], fill=(0, 255, 255), width=1)
    dr.line([(ix + z["hx"] + z["hw"], 0), (ix + z["hx"] + z["hw"], h - 1)], fill=(0, 128, 255), width=1)
    dr.line([(0, iy), (w - 1, iy)], fill=(255, 255, 0), width=1)
    dr.line([(0, iy + z["hh"]), (w - 1, iy + z["hh"])], fill=(255, 128, 0), width=1)
    dr.rectangle([ix + z["hx"], iy + z["hy"], ix + z["hx"] + z["hw"], iy + z["hy"] + z["hh"]],
                 outline=(255, 0, 0), width=1)
    l, t = max(0, ix - 100), max(0, iy - 110)
    r, b = min(w, ix + 160), min(h, iy + 190)
    img.crop((l, t, r, b)).resize(((r - l) * 3, (b - t) * 3), 0).save(OUT)
    print("saved", OUT, "crop", (l, t, r, b))


if __name__ == "__main__":
    main()
