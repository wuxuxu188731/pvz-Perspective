using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace PvzEsp
{
    /// <summary>
    /// Read-only access to the PlantsVsZombies process. Never requests write access
    /// and never throws to the UI thread: every failure is reported through
    /// Connected / EnsureAttached() / zero or empty read results.
    /// </summary>
    internal sealed class GameMemory : IDisposable
    {
        private const int ProcessVmRead = 0x0010;
        private const int ProcessQueryInformation = 0x0400;
        private const string TargetProcessName = "PlantsVsZombies";

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr OpenProcess(int desiredAccess, bool inheritHandle, int processId);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool ReadProcessMemory(
            IntPtr process,
            IntPtr baseAddress,
            byte[] buffer,
            int size,
            out int bytesRead);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);

        private IntPtr _handle;
        private int _baseAddress;
        private Process _process;
        private bool _disposed;

        public IntPtr Handle
        {
            get { return _handle; }
        }

        public int BaseAddress
        {
            get { return _baseAddress; }
        }

        public int ProcessId
        {
            get
            {
                Process process = _process;
                if (process == null)
                {
                    return 0;
                }
                try
                {
                    return process.Id;
                }
                catch (Exception)
                {
                    return 0;
                }
            }
        }

        public bool Connected
        {
            get
            {
                if (_disposed || _handle == IntPtr.Zero || _process == null)
                {
                    return false;
                }
                try
                {
                    return !_process.HasExited;
                }
                catch (Exception)
                {
                    return false;
                }
            }
        }

        /// <summary>
        /// Re-attaches when the game starts or restarts. Safe to call every frame.
        /// Returns false when the game is not running.
        /// </summary>
        public bool EnsureAttached()
        {
            if (_disposed)
            {
                return false;
            }

            if (_handle != IntPtr.Zero && _process != null)
            {
                try
                {
                    if (!_process.HasExited)
                    {
                        return true;
                    }
                }
                catch (Exception)
                {
                }
                Detach();
            }

            return Attach();
        }

        private bool Attach()
        {
            if (_disposed)
            {
                return false;
            }

            try
            {
                if (_process == null)
                {
                    _process = FindTargetProcess();
                }
                if (_process == null)
                {
                    return false;
                }
                if (_process.HasExited)
                {
                    Detach();
                    return false;
                }

                IntPtr handle = OpenProcess(ProcessVmRead | ProcessQueryInformation, false, _process.Id);
                if (handle == IntPtr.Zero)
                {
                    return false;
                }

                int baseAddress = 0;
                try
                {
                    ProcessModule module = _process.MainModule;
                    if (module != null)
                    {
                        baseAddress = module.BaseAddress.ToInt32();
                    }
                }
                catch (Exception)
                {
                    // The module list can be unreadable while the process is
                    // still starting up or shutting down. Retry next frame.
                    CloseHandle(handle);
                    return false;
                }

                _handle = handle;
                _baseAddress = baseAddress;
                return true;
            }
            catch (Exception)
            {
                Detach();
                return false;
            }
        }

        private static Process FindTargetProcess()
        {
            try
            {
                Process[] processes = Process.GetProcessesByName(TargetProcessName);
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

        public byte[] ReadBytes(int address, int count)
        {
            if (count <= 0)
            {
                return new byte[0];
            }
            if (!EnsureAttached())
            {
                return new byte[0];
            }

            byte[] buffer = new byte[count];
            try
            {
                int bytesRead;
                if (!ReadProcessMemory(_handle, new IntPtr(address), buffer, count, out bytesRead))
                {
                    return new byte[0];
                }
                if (bytesRead != count)
                {
                    return new byte[0];
                }
                return buffer;
            }
            catch (Exception)
            {
                return new byte[0];
            }
        }

        public int ReadInt(int address)
        {
            byte[] data = ReadBytes(address, 4);
            if (data.Length < 4)
            {
                return 0;
            }
            return BitConverter.ToInt32(data, 0);
        }

        public uint ReadUInt(int address)
        {
            byte[] data = ReadBytes(address, 4);
            if (data.Length < 4)
            {
                return 0;
            }
            return BitConverter.ToUInt32(data, 0);
        }

        public float ReadFloat(int address)
        {
            byte[] data = ReadBytes(address, 4);
            if (data.Length < 4)
            {
                return 0f;
            }
            return BitConverter.ToSingle(data, 0);
        }

        public void Dispose()
        {
            if (_disposed)
            {
                return;
            }
            _disposed = true;
            Detach();
        }

        private void Detach()
        {
            if (_handle != IntPtr.Zero)
            {
                try
                {
                    CloseHandle(_handle);
                }
                catch (Exception)
                {
                }
                _handle = IntPtr.Zero;
            }

            _baseAddress = 0;

            if (_process != null)
            {
                try
                {
                    _process.Dispose();
                }
                catch (Exception)
                {
                }
                _process = null;
            }
        }
    }
}
