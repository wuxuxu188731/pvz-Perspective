"""Deeper Board inspection: raw fields, pointed-to buffers, wider pointer-run scan."""
import struct

import pvzlib as P

MOD_LO, MOD_HI = 0x400000, 0x400000 + 0xBC8000


def is_mod(v):
    return MOD_LO <= v < MOD_HI


pid = P.find_pid()
p = P.Proc(pid)
lawn = p.u32(0x6A9EC0)
board = p.u32(lawn + 0x768)
print("LawnApp=0x%08X Board=0x%08X sun=%d" % (lawn, board, p.i32(board + 0x5560)))

print("\n== Board raw 0x080..0x0C0 ==")
for off in range(0x80, 0xC0, 4):
    print("  +0x%03X = 0x%08X  (%d)" % (off, p.u32(board + off), p.i32(board + off)))

for name, off in (("90", 0x90), ("AC", 0xAC)):
    arr = p.u32(board + off)
    print("\n== buffer at Board+0x%s -> 0x%08X ==" % (name, arr))
    if 0x10000 <= arr < 0x7F000000:
        try:
            print(P.hexdump(p.read(arr, 0x60), arr))
        except OSError as e:
            print("  unreadable", e)

print("\n== wide pointer-run scan Board[0..0x20000] ==")
hits = []
for off in range(0, 0x20000, 4):
    try:
        v = p.u32(board + off)
    except OSError:
        continue
    if not (0x10000 <= v < 0x7F000000):
        continue
    try:
        vt = p.u32(v)
    except OSError:
        continue
    if is_mod(vt):
        hits.append((off, v, vt))

runs = []
cur = []
for h in hits:
    if cur and h[0] - cur[-1][0] == 4:
        cur.append(h)
    else:
        if cur:
            runs.append(cur)
        cur = [h]
if cur:
    runs.append(cur)
for r in runs:
    if len(r) >= 2:
        print("  Board+0x%04X..0x%04X n=%d vts=%s" %
              (r[0][0], r[-1][0], len(r),
               ", ".join("0x%X" % v for v in sorted(set(x[2] for x in r))[:6])))
