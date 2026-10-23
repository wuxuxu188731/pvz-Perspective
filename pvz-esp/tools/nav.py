"""Drive the PvZ window: info / move / focus / click (client coords) / key."""
import ctypes
import os
import sys
import time
from ctypes import wintypes as wt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pvzlib as P  # noqa: E402

# Physical pixel coordinates everywhere (screen is 125% scaled).
try:
    ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
except Exception:
    pass

u32 = P.u32
k32 = P.k32

u32.SetForegroundWindow.argtypes = [wt.HWND]
u32.SetForegroundWindow.restype = wt.BOOL
u32.GetWindowRect.argtypes = [wt.HWND, ctypes.c_void_p]
u32.GetClientRect.argtypes = [wt.HWND, ctypes.c_void_p]
u32.ClientToScreen.argtypes = [wt.HWND, ctypes.c_void_p]
u32.EnumWindows.argtypes = [ctypes.c_void_p, wt.LPARAM]
u32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
u32.GetWindowTextLengthW.argtypes = [wt.HWND]
u32.IsWindowVisible.argtypes = [wt.HWND]
u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.c_void_p]
u32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
u32.PostMessageW.restype = wt.BOOL
u32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                             ctypes.c_int, ctypes.c_int, wt.UINT]
u32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
u32.mouse_event.argtypes = [wt.DWORD, wt.DWORD, wt.DWORD, wt.DWORD, ctypes.c_size_t]
u32.keybd_event.argtypes = [wt.BYTE, wt.BYTE, wt.DWORD, ctypes.c_size_t]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def windows_of(pid):
    out = []
    CB = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def _cb(hwnd, _lp):
        wp = wt.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
        if wp.value == pid and u32.IsWindowVisible(hwnd):
            n = u32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(hwnd, buf, n + 1)
            out.append((hwnd, buf.value))
        return True

    u32.EnumWindows(CB(_cb), 0)
    return out


def main_window(pid):
    cands = windows_of(pid)
    cands.sort(key=lambda t: -len(t[1]))
    if not cands:
        raise SystemExit("no visible window for pid %d" % pid)
    return cands[0][0]


def rects(hwnd):
    wr = RECT()
    cr = RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(wr))
    u32.GetClientRect(hwnd, ctypes.byref(cr))
    pt = POINT(0, 0)
    u32.ClientToScreen(hwnd, ctypes.byref(pt))
    return (wr.left, wr.top, wr.right, wr.bottom), (cr.right, cr.bottom), (pt.x, pt.y)


def click(client_x, client_y, hwnd=None):
    """Click by posting WM_* messages in client coords: works even when occluded."""
    pid = P.find_pid()
    if pid is None:
        raise SystemExit("game not running")
    hwnd = hwnd or main_window(pid)
    lp = ((client_y & 0xFFFF) << 16) | (client_x & 0xFFFF)
    u32.PostMessageW(hwnd, 0x0200, 0, lp)       # WM_MOUSEMOVE
    time.sleep(0.03)
    u32.PostMessageW(hwnd, 0x0201, 0x0001, lp)  # WM_LBUTTONDOWN (MK_LBUTTON)
    time.sleep(0.05)
    u32.PostMessageW(hwnd, 0x0202, 0, lp)       # WM_LBUTTONUP
    time.sleep(0.03)
    return ("post", client_x, client_y)


def real_click(client_x, client_y, hwnd=None):
    pid = P.find_pid()
    hwnd = hwnd or main_window(pid)
    _, _, (ox, oy) = rects(hwnd)
    sx, sy = ox + client_x, oy + client_y
    u32.SetForegroundWindow(hwnd)
    time.sleep(0.15)
    u32.SetCursorPos(sx, sy)
    time.sleep(0.08)
    u32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.06)
    u32.mouse_event(0x0004, 0, 0, 0, 0)
    return ("real", sx, sy)


def key(vk, hold=0.06):
    u32.keybd_event(vk, 0, 0, 0)
    time.sleep(hold)
    u32.keybd_event(vk, 0, 2, 0)


def cmd_info():
    pid = P.find_pid()
    if pid is None:
        print("game not running")
        return 1
    for hwnd, title in windows_of(pid):
        wr, cs, co = rects(hwnd)
        print("hwnd=0x%X title=%r" % (hwnd, title))
        print("  window_rect=%s size=%dx%d" % (wr, wr[2] - wr[0], wr[3] - wr[1]))
        print("  client=%dx%d origin=%s" % (cs[0], cs[1], co))
    return 0


def cmd_move(x, y):
    pid = P.find_pid()
    hwnd = main_window(pid)
    u32.SetWindowPos(hwnd, None, int(x), int(y), 0, 0, 0x0001 | 0x0004 | 0x0010)
    time.sleep(0.2)
    return cmd_info()


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    try:
        if cmd == "info":
            return cmd_info()
        if cmd == "move":
            return cmd_move(argv[1], argv[2])
        if cmd == "focus":
            pid = P.find_pid()
            u32.SetForegroundWindow(main_window(pid))
            print("focused")
            return 0
        if cmd == "click":
            print("clicked", click(int(argv[1]), int(argv[2])))
            return 0
        if cmd == "rclick":
            print("real clicked", real_click(int(argv[1]), int(argv[2])))
            return 0
        if cmd == "key":
            key(int(argv[1], 0))
            print("key sent")
            return 0
        print("unknown command", cmd)
        return 2
    except IndexError:
        print("missing args")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
