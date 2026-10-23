"""Dump zombie / plant arrays using the documented PvZ 1.0.0.1051 layout."""
import struct
import sys

import pvzlib as P

ZOMBIE_STRIDE = 0x15C
PLANT_STRIDE = 0x14C

pid = P.find_pid()
p = P.Proc(pid)
lawn = p.u32(0x6A9EC0)
board = p.u32(lawn + 0x768)
print("LawnApp=0x%08X Board=0x%08X sun=%d" % (lawn, board, p.i32(board + 0x5560)))

zb = p.u32(board + 0x90)
zc = p.u32(board + 0x94)
print("\nzombie base=0x%08X count=%d  (board+0x94=%d +0x98=%d +0x9C=%d +0xA0=%d)"
      % (zb, zc, p.u32(board + 0x94), p.u32(board + 0x98), p.u32(board + 0x9C), p.u32(board + 0xA0)))
print("i   addr        app       board      imgX imgY vis row  type  state x(f)      y(f)      hp/max    acc1        acc2")
for i in range(min(zc + 3, 40)):
    o = zb + i * ZOMBIE_STRIDE
    try:
        app = p.u32(o)
        bd = p.u32(o + 4)
        ix = p.i32(o + 8)
        iy = p.i32(o + 0xC)
        vis = p.u8(o + 0x18)
        row = p.i32(o + 0x1C)
        typ = p.i32(o + 0x24)
        st = p.i32(o + 0x28)
        fx = p.f32(o + 0x2C)
        fy = p.f32(o + 0x30)
        hp = p.i32(o + 0xC8)
        hpm = p.i32(o + 0xCC)
        a1 = p.i32(o + 0xD0)
        a1m = p.i32(o + 0xD4)
        a2 = p.i32(o + 0xDC)
        a2m = p.i32(o + 0xE0)
        exists = p.u16(o + 0x15A)
    except OSError as e:
        print("  [%02d] read failed" % i)
        break
    print("%02d 0x%08X 0x%08X 0x%08X %4d %4d %3d %3d %5d %5d %8.2f %8.2f %5d/%-5d %4d/%-4d %4d/%-4d ex=%d"
          % (i, o, app, bd, ix, iy, vis, row, typ, st, fx, fy, hp, hpm, a1, a1m, a2, a2m, exists))

pb = p.u32(board + 0xAC)
pc = p.u32(board + 0xB0)
print("\nplant base=0x%08X count=%d (board+0xB0=%d +0xB4=%d +0xB8=%d +0xBC=%d)"
      % (pb, pc, p.u32(board + 0xB0), p.u32(board + 0xB4), p.u32(board + 0xB8), p.u32(board + 0xBC)))
print("i   addr        app       board      x   y   vis row layer type col state hp/max id")
for i in range(min(pc + 2, 40)):
    o = pb + i * PLANT_STRIDE
    try:
        app = p.u32(o)
        bd = p.u32(o + 4)
        x = p.i32(o + 8)
        y = p.i32(o + 0xC)
        vis = p.u8(o + 0x18)
        row = p.i32(o + 0x1C)
        layer = p.i32(o + 0x20)
        typ = p.i32(o + 0x24)
        col = p.i32(o + 0x28)
        st = p.i32(o + 0x3C)
        hp = p.i32(o + 0x40)
        hpm = p.i32(o + 0x44)
        pid2 = p.u32(o + 0x148)
        gone = p.u8(o + 0x141)
    except OSError:
        print("  [%02d] read failed" % i)
        break
    print("%02d 0x%08X 0x%08X 0x%08X %3d %3d %3d %3d %5x %4d %3d %5d %5d/%-5d %08X gone=%d"
          % (i, o, app, bd, x, y, vis, row, layer, typ, col, st, hp, hpm, pid2, gone))
