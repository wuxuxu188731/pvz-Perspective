"""Find contiguous object-pointer runs inside the Board object (zombie/plant arrays)."""
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

hits = []
for off in range(0, 0x5600, 4):
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

print("\nobject-pointer runs (>=2 consecutive dwords):")
for r in runs:
    vts = sorted(set(x[2] for x in r))
    print("  Board+0x%03X .. 0x%03X  n=%d  vtable(s)=%s" %
          (r[0][0], r[-1][0], len(r), ", ".join("0x%X" % v for v in vts)))

print("\n--- detail of the 3 longest runs ---")
for r in sorted(runs, key=lambda x: -len(x))[:3]:
    print("\n== Board+0x%03X run n=%d ==" % (r[0][0], len(r)))
    for off, v, vt in r[:12]:
        print("   +0x%03X -> 0x%08X vt=0x%08X" % (off, v, vt))

print("\n--- hexdump/floats of first object of the longest run ---")
r = max(runs, key=len)
obj = r[0][1]
data = p.read(obj, 0x1C0)
print(P.hexdump(data, obj))
print("\nfloats 0.5..1200:")
line = []
for o in range(0, len(data) - 4, 4):
    f = struct.unpack_from("<f", data, o)[0]
    if 0.5 <= f <= 1200.0:
        line.append("+0x%03X=%g" % (o, f))
print("  " + "  ".join(line))
print("\nints 0..300:")
line = []
for o in range(0, len(data) - 4, 4):
    v = struct.unpack_from("<i", data, o)[0]
    if 0 <= v <= 300:
        line.append("+0x%03X=%d" % (o, v))
print("  " + "  ".join(line))
