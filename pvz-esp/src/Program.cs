using System;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

namespace PvzEsp
{
    internal static class Program
    {
        private const string MutexName = "PvzEsp_Overlay_SingleInstance";

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool SetProcessDpiAwarenessContext(IntPtr dpiContext);

        [DllImport("shcore.dll", SetLastError = true)]
        private static extern int SetProcessDpiAwareness(int awareness);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool SetProcessDPIAware();

        [STAThread]
        private static void Main()
        {
            EnableDpiAwareness();

            bool createdNew = true;
            Mutex mutex = null;
            try
            {
                mutex = new Mutex(true, MutexName, out createdNew);
            }
            catch (Exception)
            {
                // Single-instance protection is best effort; keep running if the
                // mutex cannot be created for any reason.
                createdNew = true;
                mutex = null;
            }

            if (!createdNew)
            {
                if (mutex != null)
                {
                    mutex.Dispose();
                }
                return;
            }

            try
            {
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                using (OverlayForm form = new OverlayForm())
                {
                    Application.Run(form);
                }
            }
            finally
            {
                if (mutex != null)
                {
                    try
                    {
                        mutex.ReleaseMutex();
                    }
                    catch (Exception)
                    {
                    }
                    mutex.Dispose();
                }
            }
        }

        private static void EnableDpiAwareness()
        {
            // 1) Per-monitor v2 (Windows 10 1703+). DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4.
            try
            {
                if (SetProcessDpiAwarenessContext(new IntPtr(-4)))
                {
                    return;
                }
            }
            catch (Exception)
            {
            }

            // 2) Per-monitor (Windows 8.1+). PROCESS_PER_MONITOR_DPI_AWARE == 2.
            try
            {
                if (SetProcessDpiAwareness(2) == 0)
                {
                    return;
                }
            }
            catch (Exception)
            {
            }

            // 3) System DPI aware (Windows Vista+).
            try
            {
                SetProcessDPIAware();
            }
            catch (Exception)
            {
            }
        }
    }
}
