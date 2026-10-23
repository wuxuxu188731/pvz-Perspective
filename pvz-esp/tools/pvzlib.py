"""Minimal Win32 process/memory helpers for inspecting a 32-bit game (Python 3.10 x64)."""
import ctypes
import struct
import time
from ctypes import wintypes as wt

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400

MEM_COMMIT = 0x1000
PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100

READABLE = (0x02, 0x04, 0x08, 0x20, 0x40, 0x80)  # R/RW/RWX/ER/ERW/EWC


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * 260),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
    ]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [
    wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
k32.WriteProcessMemory.restype = wt.BOOL
k32.WriteProcessMemory.argtypes = [
    wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [
    wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    ctypes.c_size_t,
]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.Process32FirstW.restype = wt.BOOL
k32.Process32NextW.restype = wt.BOOL


def find_pid(exe_name="PlantsVsZombies.exe"):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == wt.HANDLE(-1).value:
        return None
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    found = None
    try:
        ok = k32.Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            if pe.szExeFile.lower() == exe_name.lower():
                found = int(pe.th32ProcessID)
                break
            ok = k32.Process32NextW(snap, ctypes.byref(pe))
    finally:
        k32.CloseHandle(snap)
    return found


class Proc:
    def __init__(self, pid, write=False):
        self.pid = pid
        access = PROCESS_VM_READ | PROCESS_QUERY_INFORMATION
        if write:
            access |= PROCESS_VM_WRITE | PROCESS_VM_OPERATION
        self.h = k32.OpenProcess(access, False, pid)
        if not self.h:
            raise OSError("OpenProcess failed: %d" % ctypes.get_last_error())
        self.write_ok = write
        self.base = self._find_base()

    def close(self):
        if self.h:
            k32.CloseHandle(self.h)
            self.h = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # ---------- raw ----------
    def read(self, addr, size):
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t(0)
        ok = k32.ReadProcessMemory(
            self.h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)
        )
        if not ok or got.value != size:
            raise OSError(
                "RPM fail at 0x%X size %d (err %d, got %d)"
                % (addr, size, ctypes.get_last_error(), got.value)
            )
        return buf.raw[:got.value]

    def can_read(self, addr, size=4):
        try:
            self.read(addr, size)
            return True
        except OSError:
            return False

    def write(self, addr, data):
        if not self.write_ok:
            raise OSError("opened read-only")
        buf = ctypes.create_string_buffer(data, len(data))
        put = ctypes.c_size_t(0)
        ok = k32.WriteProcessMemory(
            self.h, ctypes.c_void_p(addr), buf, len(data), ctypes.byref(put)
        )
        if not ok or put.value != len(data):
            raise OSError("WPM fail at 0x%X (err %d)" % (addr, ctypes.get_last_error()))
        return put.value

    def u8(self, a):
        return self.read(a, 1)[0]

    def u16(self, a):
        return struct.unpack("<H", self.read(a, 2))[0]

    def u32(self, a):
        return struct.unpack("<I", self.read(a, 4))[0]

    def i32(self, a):
        return struct.unpack("<i", self.read(a, 4))[0]

    def f32(self, a):
        return struct.unpack("<f", self.read(a, 4))[0]

    def ptr(self, a):
        """Dereference a 32-bit pointer slot; returns 0 for null."""
        return self.u32(a)

    # ---------- modules ----------
    def _find_base(self):
        # No ASLR on the target: preferred base holds the PE header.
        try:
            hdr = self.read(0x400000, 0x40)
            if hdr[:2] == b"MZ":
                e = struct.unpack("<I", hdr[0x3C:0x40])[0]
                if self.read(0x400000 + e, 4) == b"PE\0\0":
                    return 0x400000
        except OSError:
            pass
        for b, size, prot in self.regions():
            try:
                if self.read(b, 2) == b"MZ":
                    e = self.u32(b + 0x3C)
                    if self.read(b + e, 4) == b"PE\0\0":
                        return b
            except OSError:
                continue
        raise OSError("module base not found")

    def regions(self):
        """Yield (base, size, protect) for committed readable regions."""
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        while addr < 0x80000000:
            rc = k32.VirtualQueryEx(self.h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                    ctypes.sizeof(mbi))
            if rc == 0:
                break
            base = mbi.BaseAddress or 0
            size = int(mbi.RegionSize)
            if mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in READABLE \
                    and not (mbi.Protect & PAGE_GUARD):
                yield base, size, mbi.Protect
            nxt = base + size
            if nxt <= addr:
                break
            addr = nxt

    # ---------- scanning ----------
    def scan(self, needle, start=0x00010000, end=0x80000000, limit=50, chunk=1 << 20):
        """Find byte patterns in committed readable memory. Returns list of addresses."""
        hits = []
        pat = bytes(needle)
        n = len(pat)
        for b, size, _prot in self.regions():
            if b + size <= start or b >= end:
                continue
            off = 0
            carry = b""
            carry_addr = 0
            while off < size:
                step = min(chunk, size - off)
                try:
                    data = self.read(b + off, step)
                except OSError:
                    off += step
                    carry = b""
                    continue
                blob = carry + data
                base_addr = carry_addr if carry else b + off
                i = 0
                while True:
                    j = blob.find(pat, i)
                    if j < 0:
                        break
                    hits.append(base_addr + j)
                    i = j + 1
                    if len(hits) >= limit:
                        return hits
                keep = min(n - 1, len(blob))
                carry = blob[-keep:] if keep else b""
                carry_addr = base_addr + len(blob) - keep
                off += step
        return hits

    def iter_dwords(self, start, end, chunk=1 << 20):
        for b, size, _p in self.regions():
            lo = max(b, start)
            hi = min(b + size, end)
            if hi <= lo:
                continue
            off = lo
            while off < hi:
                step = min(chunk, hi - off) & ~3
                if step <= 0:
                    break
                try:
                    data = self.read(off, step)
                except OSError:
                    off += chunk
                    continue
                for k in range(0, step, 4):
                    yield off + k, struct.unpack_from("<I", data, k)[0]
                off += step


def hexdump(data, base=0, width=16):
    out = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hexs = " ".join("%02X" % c for c in chunk)
        txt = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        out.append("%08X  %-*s  %s" % (base + i, width * 3, hexs, txt))
    return "\n".join(out)


def read_cstr(p, addr, maxlen=64):
    raw = p.read(addr, maxlen)
    z = raw.find(b"\0")
    return raw[:z if z >= 0 else maxlen]


def main():
    pid = find_pid()
    print("pid:", pid)
    with Proc(pid) as p:
        print("base: 0x%X" % p.base)
        print("lawnapp slot: 0x%X" % p.u32(0x6A9EC0))


if __name__ == "__main__":
    main()
