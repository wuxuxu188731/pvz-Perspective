using System;
using System.Diagnostics;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace PvzEsp
{
    /// <summary>
    /// External, click-through overlay that mirrors the game's client area.
    /// The window never activates, never appears in the taskbar and is excluded
    /// from the Alt+Tab/tool window list.
    /// </summary>
    internal sealed class OverlayForm : Form
    {
        private const int WsExLayered = 0x00080000;
        private const int WsExTransparent = 0x00000020;
        private const int WsExToolWindow = 0x00000080;
        private const int WsExNoActivate = 0x08000000;

        private const int VkF8 = 0x77;
        private const int VkF9 = 0x78;
        private const int VkF10 = 0x79;
        private const int VkF11 = 0x7A;

        private const int GwOwner = 4;
        private const int TimerIntervalMs = 16;

        [StructLayout(LayoutKind.Sequential)]
        private struct RECT
        {
            public int Left;
            public int Top;
            public int Right;
            public int Bottom;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct POINT
        {
            public int X;
            public int Y;
        }

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool GetClientRect(IntPtr hWnd, out RECT clientRect);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool ClientToScreen(IntPtr hWnd, ref POINT point);

        [DllImport("user32.dll")]
        private static extern short GetAsyncKeyState(int virtualKey);

        [DllImport("user32.dll")]
        private static extern bool IsWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool IsIconic(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out int processId);

        [DllImport("user32.dll")]
        private static extern IntPtr GetWindow(IntPtr hWnd, int command);

        [DllImport("user32.dll")]
        private static extern bool PrintWindow(IntPtr window, IntPtr dc, uint flags);

        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        private readonly GameMemory _memory;
        private readonly Timer _frameTimer;
        private readonly Stopwatch _clock;

        private Process _gameProcess;
        private IntPtr _gameWindow = IntPtr.Zero;
        private Rectangle _clientRect = Rectangle.Empty;

        private bool _overlayEnabled = true;
        private bool _previousF8;
        private bool _previousF9;
        private bool _previousF10;
        private bool _previousF11;
        private double _videoSeconds = -1;
        private double _lastVideoTick;
        private Bitmap _frozenFrame;
        private bool _endingInput;
        private bool _closing;

        private long _lastTickTicks;
        private double _fps;

        public OverlayForm()
        {
            _memory = new GameMemory();
            _clock = Stopwatch.StartNew();

            SetStyle(
                ControlStyles.OptimizedDoubleBuffer |
                ControlStyles.AllPaintingInWmPaint |
                ControlStyles.UserPaint,
                true);

            FormBorderStyle = FormBorderStyle.None;
            ShowInTaskbar = false;
            TopMost = true;
            StartPosition = FormStartPosition.Manual;
            BackColor = Color.Black;
            TransparencyKey = Color.Black;
            AutoScaleMode = AutoScaleMode.None;
            Text = "PvzEspOverlay";

            _frameTimer = new Timer();
            _frameTimer.Interval = TimerIntervalMs;
            _frameTimer.Tick += new EventHandler(OnFrameTick);
        }

        protected override bool ShowWithoutActivation
        {
            get { return true; }
        }

        protected override CreateParams CreateParams
        {
            get
            {
                CreateParams createParams = base.CreateParams;
                createParams.ExStyle |= WsExLayered | WsExToolWindow | WsExNoActivate;
                if (!_endingInput) createParams.ExStyle |= WsExTransparent;
                return createParams;
            }
        }

        protected override void OnLoad(EventArgs e)
        {
            base.OnLoad(e);
            _frameTimer.Start();
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            _frameTimer.Stop();
            _frameTimer.Dispose();
            _memory.Dispose();
            if (_frozenFrame != null) _frozenFrame.Dispose();

            if (_gameProcess != null)
            {
                try
                {
                    _gameProcess.Dispose();
                }
                catch (Exception)
                {
                }
                _gameProcess = null;
            }

            base.OnFormClosed(e);
        }

        private void OnFrameTick(object sender, EventArgs e)
        {
            if (_closing)
            {
                return;
            }

            long now = _clock.ElapsedTicks;
            UpdateFrameRate(now);
            PollHotkeys();
            if (_closing)
            {
                return;
            }

            try
            {
                _memory.EnsureAttached();
            }
            catch (Exception)
            {
            }

            UpdateGameWindow();
            UpdateOverlayBounds();

            double videoNow = _clock.Elapsed.TotalSeconds;
            double videoDelta = videoNow - _lastVideoTick;
            _lastVideoTick = videoNow;
            // 切走游戏或 F8 隐藏时暂停演出计时，方便录屏准备。
            if (_videoSeconds >= 0 && Visible)
            {
                double previous = _videoSeconds;
                _videoSeconds = Math.Min(22, _videoSeconds + videoDelta);
                if (previous < 21 && _videoSeconds >= 21) CaptureEndingFrame();
                if (!_endingInput && _videoSeconds >= 21.6)
                {
                    _endingInput = true;
                    UpdateStyles();
                }
            }

            if (Visible)
            {
                Invalidate();
            }
        }

        private void UpdateFrameRate(long now)
        {
            if (_lastTickTicks != 0)
            {
                long delta = now - _lastTickTicks;
                if (delta > 0)
                {
                    double instant = Stopwatch.Frequency / (double)delta;
                    if (instant > 1000.0)
                    {
                        instant = 1000.0;
                    }
                    if (_fps <= 0.0)
                    {
                        _fps = instant;
                    }
                    else
                    {
                        _fps += (instant - _fps) * 0.1;
                    }
                }
            }
            _lastTickTicks = now;
        }

        private void PollHotkeys()
        {
            // GetAsyncKeyState's high bit is set while the key is held. Compare
            // with the previous frame so one physical press fires only once.
            bool f8Down = (GetAsyncKeyState(VkF8) & 0x8000) != 0;
            bool f9Down = (GetAsyncKeyState(VkF9) & 0x8000) != 0;
            bool f10Down = (GetAsyncKeyState(VkF10) & 0x8000) != 0;
            bool f11Down = (GetAsyncKeyState(VkF11) & 0x8000) != 0;

            if (f8Down && !_previousF8)
            {
                _overlayEnabled = !_overlayEnabled;
            }
            if (f9Down && !_previousF9)
            {
                _closing = true;
                _frameTimer.Stop();
                Close();
                return;
            }
            int foregroundId;
            GetWindowThreadProcessId(GetForegroundWindow(), out foregroundId);
            bool gameForeground = _gameProcess != null && foregroundId == _gameProcess.Id;
            if (f10Down && !_previousF10 && gameForeground)
            {
                ResetVideo();
                _overlayEnabled = true;
                _videoSeconds = 0;
                _lastVideoTick = _clock.Elapsed.TotalSeconds;
            }
            if (f11Down && !_previousF11) ResetVideo();

            _previousF8 = f8Down;
            _previousF9 = f9Down;
            _previousF10 = f10Down;
            _previousF11 = f11Down;
        }

        private void ResetVideo()
        {
            _videoSeconds = -1;
            if (_frozenFrame != null) { _frozenFrame.Dispose(); _frozenFrame = null; }
            if (_endingInput) { _endingInput = false; UpdateStyles(); }
        }

        private void CaptureEndingFrame()
        {
            Bitmap frame = new Bitmap(Math.Max(1, ClientSize.Width), Math.Max(1, ClientSize.Height));
            try
            {
                using (Graphics g = Graphics.FromImage(frame))
                {
                    IntPtr dc = g.GetHdc();
                    try
                    {
                        // 只捕获游戏窗口，不把透视、白圈或其他窗口拍进结尾。
                        if (!PrintWindow(_gameWindow, dc, 3)) return;
                    }
                    finally { g.ReleaseHdc(dc); }
                }
                _frozenFrame = frame;
                frame = null;
            }
            finally { if (frame != null) frame.Dispose(); }
        }

        protected override void OnMouseDown(MouseEventArgs e)
        {
            if (_endingInput && e.Button == MouseButtons.Left && ClientSize.Width > 0 && ClientSize.Height > 0)
            {
                Point logical = new Point(e.X * 880 / ClientSize.Width, e.Y * 600 / ClientSize.Height);
                if (VideoEnding.Button.Contains(logical)) ResetVideo();
            }
            base.OnMouseDown(e);
        }

        private void UpdateGameWindow()
        {
            Process process = _gameProcess;
            if (process != null)
            {
                bool exited = false;
                try
                {
                    exited = process.HasExited;
                }
                catch (Exception)
                {
                    exited = true;
                }

                if (exited)
                {
                    try
                    {
                        process.Dispose();
                    }
                    catch (Exception)
                    {
                    }
                    _gameProcess = null;
                    _gameWindow = IntPtr.Zero;
                    process = null;
                }
            }

            if (process == null)
            {
                process = FindGameProcess();
                _gameProcess = process;
                _gameWindow = IntPtr.Zero;
            }

            if (process == null)
            {
                _gameWindow = IntPtr.Zero;
                return;
            }

            IntPtr window = IntPtr.Zero;
            try
            {
                window = process.MainWindowHandle;
            }
            catch (Exception)
            {
                window = IntPtr.Zero;
            }

            if (window != IntPtr.Zero && !IsWindow(window))
            {
                // The cached main-window handle was recreated; ask again.
                try
                {
                    process.Refresh();
                }
                catch (Exception)
                {
                }
                try
                {
                    window = process.MainWindowHandle;
                }
                catch (Exception)
                {
                    window = IntPtr.Zero;
                }
                if (window != IntPtr.Zero && !IsWindow(window))
                {
                    window = IntPtr.Zero;
                }
            }

            if (window == IntPtr.Zero)
            {
                window = FindMainWindowForProcess(process.Id);
            }

            _gameWindow = window;
        }

        private static Process FindGameProcess()
        {
            try
            {
                Process[] processes = Process.GetProcessesByName("PlantsVsZombies");
                if (processes == null || processes.Length == 0)
                {
                    return null;
                }

                Process chosen = processes[0];
                for (int i = 1; i < processes.Length; i++)
                {
                    try
                    {
                        processes[i].Dispose();
                    }
                    catch (Exception)
                    {
                    }
                }
                return chosen;
            }
            catch (Exception)
            {
                return null;
            }
        }

        private static IntPtr FindMainWindowForProcess(int processId)
        {
            IntPtr found = IntPtr.Zero;
            EnumWindows(
                delegate(IntPtr hWnd, IntPtr lParam)
                {
                    int ownerProcessId;
                    GetWindowThreadProcessId(hWnd, out ownerProcessId);
                    if (ownerProcessId != processId)
                    {
                        return true;
                    }
                    if (!IsWindowVisible(hWnd) || IsIconic(hWnd))
                    {
                        return true;
                    }
                    if (GetWindow(hWnd, GwOwner) != IntPtr.Zero)
                    {
                        return true;
                    }

                    RECT clientRect;
                    if (!GetClientRect(hWnd, out clientRect))
                    {
                        return true;
                    }
                    if (clientRect.Right - clientRect.Left <= 0 || clientRect.Bottom - clientRect.Top <= 0)
                    {
                        return true;
                    }

                    found = hWnd;
                    return false;
                },
                IntPtr.Zero);
            return found;
        }

        private void UpdateOverlayBounds()
        {
            IntPtr window = _gameWindow;
            if (window == IntPtr.Zero || !IsWindow(window))
            {
                HideOverlay();
                return;
            }

            if (IsIconic(window) || !IsWindowVisible(window))
            {
                HideOverlay();
                return;
            }

            int foregroundProcessId;
            GetWindowThreadProcessId(GetForegroundWindow(), out foregroundProcessId);
            if (_gameProcess == null || foregroundProcessId != _gameProcess.Id)
            {
                HideOverlay();
                return;
            }

            RECT clientRect;
            if (!GetClientRect(window, out clientRect))
            {
                HideOverlay();
                return;
            }

            int width = clientRect.Right - clientRect.Left;
            int height = clientRect.Bottom - clientRect.Top;
            if (width <= 0 || height <= 0)
            {
                HideOverlay();
                return;
            }

            POINT origin;
            origin.X = 0;
            origin.Y = 0;
            if (!ClientToScreen(window, ref origin))
            {
                HideOverlay();
                return;
            }

            Rectangle screenRect = new Rectangle(origin.X, origin.Y, width, height);
            _clientRect = screenRect;

            if (!_overlayEnabled)
            {
                if (Visible)
                {
                    Visible = false;
                }
                return;
            }

            if (Bounds != screenRect)
            {
                Bounds = screenRect;
            }
            if (!Visible)
            {
                Visible = true;
            }
        }

        private void HideOverlay()
        {
            _clientRect = Rectangle.Empty;
            if (Visible)
            {
                Visible = false;
            }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics graphics = e.Graphics;
            graphics.Clear(Color.Black);

            bool connected = false;
            try
            {
                connected = _memory.Connected;
            }
            catch (Exception)
            {
            }

            if (_videoSeconds >= 21)
                VideoEnding.Draw(graphics, ClientSize, _frozenFrame, _videoSeconds >= 21.6);
            else
            {
                Renderer.VideoSeconds = _videoSeconds;
                Renderer.Draw(graphics, _clientRect, _memory, _fps, connected);
            }
            base.OnPaint(e);
        }
    }
}
