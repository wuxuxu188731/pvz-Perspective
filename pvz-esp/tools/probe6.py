"""Measure real zombie/plant struct stride by finding object headers."""
import struct

import pvzlib as P

pid = P.find_pid()
p = P.Proc(pid)
lawn = p.u32(0x6A9EC0)
board = p.u32(lawn + 0x768)
zb = p.u32(board + 0x90)
pb = p.u32(board + 0xAC)
print("Board=0x%08X sun=%d zombieBase=0x%08X plantBase=0x%08X"
      % (board, p.i32(board + 0x5560), zb, pb))

needle = struct.pack("<I", lawn)


def find_headers(base, span):
    try:
        data = p.read(base, span)
    except OSError:
        return []
    out = []
    i = 0
    while True:
        j = data.find(needle, i)
        if j < 0 or j % 4:
            if j < 0:
                break
            i = j + 1
            continue
        # verify Board pointer follows
        if j + 8 <= len(data):
            bd = struct.unpack_from("<I", data, j + 4)[0]
            if bd == board:
                out.append(base + j)
        i = j + 4
    return out


zheads = find_headers(zb, 0x8000)
print("\nzombie headers (%d):" % len(zheads))
prev = None
for a in zheads:
    d = "" if prev is None else " +0x%X" % (a - prev)
    print("  0x%08X%s" % (a, d))
    prev = a

pheads = find_headers(pb, 0x8000)
print("\nplant headers (%d):" % len(pheads))
prev = None
for a in pheads:
    d = "" if prev is None else " +0x%X" % (a - prev)
    print("  0x%08X%s" % (a, d))
    prev = a
