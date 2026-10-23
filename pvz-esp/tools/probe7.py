"""Full zombie/plant slot dump with the mod's 0x204 stride."""
import pvzlib as P

STRIDE = 0x204

pid = P.find_pid()
p = P.Proc(pid)
lawn = p.u32(0x6A9EC0)
board = p.u32(lawn + 0x768)
zb = p.u32(board + 0x90)
pb = p.u32(board + 0xAC)
sun = p.i32(board + 0x5560)
print("Board=0x%08X sun=%d zBase=0x%08X pBase=0x%08X" % (board, sun, zb, pb))
print("zcap=%d znext=%d zlive=%d | pcap=%d pnext=%d plive=%d"
      % (p.u32(board + 0x94), p.u32(board + 0x9C), p.u32(board + 0xA0),
         p.u32(board + 0xB0), p.u32(board + 0xB8), p.u32(board + 0xBC)))

print("\n=== ZOMBIES (stride 0x204) ===")
print("i  addr        vis row typ state  x(f)     y(f)   imgX imgY  hp/max  exists died  hit(x,y,w,h)")
for i in range(p.u32(board + 0x94)):
    o = zb + i * STRIDE
    d = p.read(o, 0x160)
    app = int.from_bytes(d[0:4], "little")
    if app != lawn:
        print("%02d 0x%08X  <not a zombie slot>" % (i, o))
        continue
    import struct
    vis = d[0x18]
    row = struct.unpack_from("<i", d, 0x1C)[0]
    typ = struct.unpack_from("<i", d, 0x24)[0]
    st = struct.unpack_from("<i", d, 0x28)[0]
    fx = struct.unpack_from("<f", d, 0x2C)[0]
    fy = struct.unpack_from("<f", d, 0x30)[0]
    ix = struct.unpack_from("<i", d, 0x08)[0]
    iy = struct.unpack_from("<i", d, 0x0C)[0]
    hp = struct.unpack_from("<i", d, 0xC8)[0]
    hpm = struct.unpack_from("<i", d, 0xCC)[0]
    a1 = struct.unpack_from("<i", d, 0xD0)[0]
    a1m = struct.unpack_from("<i", d, 0xD4)[0]
    a2 = struct.unpack_from("<i", d, 0xDC)[0]
    a2m = struct.unpack_from("<i", d, 0xE0)[0]
    gone = struct.unpack_from("<i", d, 0xEC)[0]
    ex = struct.unpack_from("<H", d, 0x15A)[0]
    hx, hy, hw, hh = struct.unpack_from("<4i", d, 0x8C)
    ax, ay, aw, ah = struct.unpack_from("<4i", d, 0x9C)
    print("%02d 0x%08X %d %3d %3d %5d %8.2f %8.2f %4d %4d %4d/%-4d %5d %5d  hit(%d,%d,%d,%d) atk(%d,%d,%d,%d) acc1=%d/%d acc2=%d/%d"
          % (i, o, vis, row, typ, st, fx, fy, ix, iy, hp, hpm, ex, gone, hx, hy, hw, hh, ax, ay, aw, ah, a1, a1m, a2, a2m))

print("\n=== PLANTS (stride 0x204) ===")
print("i  addr        vis row col typ state hp/max  x   y   id")
import struct
for i in range(p.u32(board + 0xB0)):
    o = pb + i * STRIDE
    d = p.read(o, 0x160)
    app = int.from_bytes(d[0:4], "little")
    if app != lawn:
        print("%02d 0x%08X  <empty>" % (i, o))
        continue
    vis = d[0x18]
    row = struct.unpack_from("<i", d, 0x1C)[0]
    col = struct.unpack_from("<i", d, 0x28)[0]
    typ = struct.unpack_from("<i", d, 0x24)[0]
    st = struct.unpack_from("<i", d, 0x3C)[0]
    hp = struct.unpack_from("<i", d, 0x40)[0]
    hpm = struct.unpack_from("<i", d, 0x44)[0]
    x = struct.unpack_from("<i", d, 0x08)[0]
    y = struct.unpack_from("<i", d, 0x0C)[0]
    pid2 = struct.unpack_from("<I", d, 0x148)[0]
    print("%02d 0x%08X %d %3d %3d %3d %5d %5d/%-5d %3d %3d %08X" % (i, o, vis, row, col, typ, st, hp, hpm, x, y, pid2))
