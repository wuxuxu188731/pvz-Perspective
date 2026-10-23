"""Locate LawnApp -> Board and inspect candidate object pointers."""
import struct
import sys

import pvzlib as P

MOD_LO = 0x400000
MOD_HI = 0x400000 + 0xBC8000


def is_mod(v):
    return MOD_LO <= v < MOD_HI


pid = P.find_pid()
if pid is None:
    raise SystemExit("game not running")
p = P.Proc(pid)
print("pid", pid, "base 0x%X" % p.base)

lawn = p.u32(0x6A9EC0)
print("LawnApp = 0x%08X" % lawn)
try:
    print("LawnApp vtable = 0x%08X" % p.u32(lawn))
except OSError as e:
    print("vt read failed", e)
    raise SystemExit(1)

print("\n-- object-like pointers in LawnApp[0..0xF00] --")
cands = []
for off in range(0, 0xF00, 4):
    try:
        v = p.u32(lawn + off)
    except OSError:
        continue
    if not (0x10000 <= v < 0x7F000000) or (v & 3):
        continue
    try:
        vt = p.u32(v)
    except OSError:
        continue
    if is_mod(vt):
        print("  Lawn+0x%03X -> 0x%08X  vtable 0x%08X" % (off, v, vt))
        cands.append((off, v, vt))

print("\n-- probing classic Board fields on each candidate --")
for off, v, vt in cands:
    info = []
    for probe in (0x5560, 0x5580, 0x55A0, 0x55F8):
        try:
            info.append("+0x%X=%d" % (probe, p.i32(v + probe)))
        except OSError:
            info.append("+0x%X=?" % probe)
    # zombie / plant array guesses
    for probe in (0x8C, 0x90, 0x94, 0x98, 0xAC, 0xB0, 0xB4, 0xB8):
        try:
            val = p.u32(v + probe)
            info.append("+0x%X=0x%X" % (probe, val))
        except OSError:
            pass
    print("  Lawn+0x%03X -> 0x%08X vt=0x%08X  %s" % (off, v, vt, "  ".join(info)))

print("\n-- raw dwords at LawnApp+0x760..0x790 --")
for off in range(0x760, 0x790, 4):
    try:
        print("  +0x%03X = 0x%08X" % (off, p.u32(lawn + off)))
    except OSError:
        print("  +0x%03X = ?" % off)
