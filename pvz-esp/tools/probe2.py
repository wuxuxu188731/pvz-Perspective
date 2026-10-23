"""Dump Board object arrays and search for float fields that look like screen coords."""
import struct
import sys

import pvzlib as P

MOD_LO, MOD_HI = 0x400000, 0x400000 + 0xBC8000


def is_mod(v):
    return MOD_LO <= v < MOD_HI


pid = P.find_pid()
p = P.Proc(pid)
lawn = p.u32(0x6A9EC0)
board = p.u32(lawn + 0x768)
print("LawnApp=0x%08X Board=0x%08X  sun=%d" % (lawn, board, p.i32(board + 0x5560)))

for label, off in (("A", 0x90), ("B", 0xAC)):
    arr = p.u32(board + off)
    cnt_field = p.u32(board + off + 4)
    nxt = p.u32(board + off + 8)
    print("\n== %s @ Board+0x%X arr=0x%08X count=0x%X next=0x%X" % (label, off, arr, cnt_field, nxt))
    if not (0x10000 <= arr < 0x7F000000):
        print("   not a pointer")
        continue
    shown = 0
    for i in range(0, 64):
        try:
            obj = p.u32(arr + 4 * i)
        except OSError:
            break
        if obj == 0:
            print("   [%02d] null" % i)
            if i > cnt_field + 4:
                break
            continue
        try:
            vt = p.u32(obj)
        except OSError:
            print("   [%02d] 0x%08X unreadable" % (i, obj))
            break
        mark = "mod" if is_mod(vt) else "   "
        print("   [%02d] obj=0x%08X vtable=0x%08X %s" % (i, obj, vt, mark))
        shown += 1
        if shown > 24:
            break

print("\n== floats in 0..1000 and small ints, per candidate object ==")
for label, off in (("A", 0x90), ("B", 0xAC)):
    arr = p.u32(board + off)
    if not (0x10000 <= arr < 0x7F000000):
        continue
    for i in range(3):
        try:
            obj = p.u32(arr + 4 * i)
            if obj == 0:
                continue
            data = p.read(obj, 0x200)
        except OSError:
            continue
        print("\n-- %s[%d] obj=0x%08X --" % (label, i, obj))
        hits = []
        for o in range(0, len(data) - 4, 4):
            f = struct.unpack_from("<f", data, o)[0]
            if 0.0 <= f <= 1200.0 and abs(f) > 0.001:
                hits.append("+0x%03X f=%g" % (o, f))
        print("   " + "  ".join(hits[:40]))
        ints = []
        for o in range(0, len(data) - 4, 4):
            v = struct.unpack_from("<i", data, o)[0]
            if 0 <= v <= 12:
                ints.append("+0x%03X i=%d" % (o, v))
        print("   small-int: " + "  ".join(ints[:40]))
