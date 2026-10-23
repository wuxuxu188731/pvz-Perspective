using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;

namespace PvzEsp
{
    /// <summary>
    /// PvZ 杂交版 v2.0 (1.0.0.1051 引擎) 僵尸透视渲染器。
    /// 偏移全部经运行时验证（Python 侧 probe5/probe6/probe7）：
    ///   LawnApp* = [0x6A9EC0]
    ///   Board*   = [LawnApp + 0x768]
    ///   Zombie*  = [Board + 0x90], 容量 = [Board + 0x94], 存活数 = [Board + 0xA0]
    ///   步长 0x204（原版 0x15C，杂交版扩展），结构头部字段与原版一致。
    /// clientRect 仅用于客户区尺寸；窗口定位由 OverlayForm 负责。
    /// 游戏逻辑坐标统一缩放到覆盖窗口的本地客户区，不能再减屏幕原点。
    /// </summary>
    internal static class Renderer
    {
        // ---- 全局指针 ----
        private const int OFF_LAWN_APP = 0x6A9EC0;
        private const int OFF_BOARD = 0x768;

        // ---- Board 字段（实测） ----
        private const int B_SUN = 0x5560;
        private const int B_WAVE_MAX = 0x5564;
        private const int B_WAVE = 0x557C;
        private const int B_ZBASE = 0x90;
        private const int B_ZCAP = 0x94;
        private const int B_ZLIVE = 0xA0;

        // ---- Zombie 字段（实测） ----
        private const int Z_STRIDE = 0x204;
        private const int Z_APP = 0x00;
        private const int Z_IMG_X = 0x08;
        private const int Z_IMG_Y = 0x0C;
        private const int Z_VISIBLE = 0x18;
        private const int Z_ROW = 0x1C;
        private const int Z_TYPE = 0x24;
        private const int Z_HIT = 0x8C;   // x, y, w, h，相对 imgX/imgY
        private const int Z_HP = 0xC8;
        private const int Z_HP_MAX = 0xCC;
        private const int Z_ACC1 = 0xD0;
        private const int Z_ACC1_MAX = 0xD4;
        private const int Z_ACC2 = 0xDC;
        private const int Z_ACC2_MAX = 0xE0;
        private const int Z_GONE = 0xEC;

        private const int MAX_SLOTS = 96;

        // 此版本游戏的原始画布为 880 x 600（见客户区截图）。
        private const float CanvasWidth = 880f;
        private const float CanvasHeight = 600f;

        private static readonly Font sSmall = new Font("Consolas", 9f, FontStyle.Bold);
        private static readonly Font sUi = new Font("Microsoft YaHei", 10f, FontStyle.Bold);

        private static readonly Color C_OUTLINE = Color.FromArgb(18, 18, 18);
        private static readonly Color C_LIVE = Color.FromArgb(0, 255, 96);
        private static readonly Color C_ARMOR = Color.FromArgb(255, 208, 0);
        private static readonly Color C_HP_BG = Color.FromArgb(72, 0, 0);
        private static readonly Color C_UI = Color.FromArgb(0, 255, 255);
        private static readonly Color C_DIM = Color.FromArgb(140, 200, 200);

        public static double VideoSeconds = -1;

        public static void Draw(Graphics g, Rectangle clientRect, GameMemory mem, double fps, bool connected)
        {
            if (g == null || clientRect.Width <= 0 || clientRect.Height <= 0) return;

            GraphicsState state = g.Save();
            try
            {
                g.TextRenderingHint = TextRenderingHint.SingleBitPerPixelGridFit;
                g.SmoothingMode = SmoothingMode.None;
                g.ScaleTransform(clientRect.Width / CanvasWidth, clientRect.Height / CanvasHeight);

                const float circleRadius = 100f;
                using (Pen circle = new Pen(Color.White, 1.5f))
                {
                    g.DrawEllipse(circle,
                        CanvasWidth / 2f - circleRadius, CanvasHeight / 2f - circleRadius,
                        circleRadius * 2f, circleRadius * 2f);
                }

                float lx = 10;
                float ly = 8;

                if (!connected)
                {
                    Text(g, sUi, "等待 PlantsVsZombies.exe ...", lx, ly, C_UI);
                    return;
                }

                int lawn = mem.ReadInt(OFF_LAWN_APP);
                if (lawn == 0)
                {
                    Text(g, sUi, "等待游戏初始化 ...", lx, ly, C_UI);
                    return;
                }

                int board = mem.ReadInt(lawn + OFF_BOARD);
                if (board == 0)
                {
                    Text(g, sUi, "不在关卡内", lx, ly, C_UI);
                    return;
                }

                int sun = mem.ReadInt(board + B_SUN);
                int zBase = mem.ReadInt(board + B_ZBASE);
                int zCap = mem.ReadInt(board + B_ZCAP);
                int zLive = mem.ReadInt(board + B_ZLIVE);
                int wave = mem.ReadInt(board + B_WAVE);
                int waveMax = mem.ReadInt(board + B_WAVE_MAX);

                int drawn = 0;
                if (zBase != 0 && zCap > 0)
                {
                    int n = zCap;
                    if (n > MAX_SLOTS) n = MAX_SLOTS;
                    int need = n * Z_STRIDE;
                    byte[] raw = mem.ReadBytes(zBase, need);
                    if (raw != null && raw.Length == need)
                    {
                        for (int i = 0; i < n; i++)
                        {
                            int o = i * Z_STRIDE;
                            if (BitConverter.ToInt32(raw, o + Z_APP) != lawn) continue;
                            if (BitConverter.ToInt32(raw, o + Z_GONE) != 0) continue;
                            if (raw[o + Z_VISIBLE] == 0) continue;

                            int hp = BitConverter.ToInt32(raw, o + Z_HP);
                            int hpm = BitConverter.ToInt32(raw, o + Z_HP_MAX);
                            if (hp <= 0 || hpm <= 0) continue;

                            int a1 = BitConverter.ToInt32(raw, o + Z_ACC1);
                            int a1m = BitConverter.ToInt32(raw, o + Z_ACC1_MAX);
                            int a2 = BitConverter.ToInt32(raw, o + Z_ACC2);
                            int a2m = BitConverter.ToInt32(raw, o + Z_ACC2_MAX);
                            if (a1m < 0) a1m = 0;
                            if (a2m < 0) a2m = 0;

                            int total = hp + Math.Max(a1, 0) + Math.Max(a2, 0);
                            int totalMax = hpm + a1m + a2m;
                            if (totalMax < total) totalMax = total;
                            if (totalMax <= 0) totalMax = 1;
                            bool armored = (a1m > 0) || (a2m > 0);

                            int imgX = BitConverter.ToInt32(raw, o + Z_IMG_X);
                            int imgY = BitConverter.ToInt32(raw, o + Z_IMG_Y);
                            int type = BitConverter.ToInt32(raw, o + Z_TYPE);

                            int hx = BitConverter.ToInt32(raw, o + Z_HIT + 0);
                            int hy = BitConverter.ToInt32(raw, o + Z_HIT + 4);
                            int hw = BitConverter.ToInt32(raw, o + Z_HIT + 8);
                            int hh = BitConverter.ToInt32(raw, o + Z_HIT + 12);
                            if (hw <= 0 || hw > 400) hw = 60;
                            if (hh <= 0 || hh > 400) hh = 115;
                            if (hx < -200 || hx > 400) hx = 0;
                            if (hy < -200 || hy > 400) hy = 0;

                            // 未校准类型保留命中框扩边；不要把普通僵尸的尺寸套给巨人等类型。
                            int bx = imgX + hx - 6;
                            int by = imgY + hy - 14;
                            int bw = hw + 50;
                            int bh = hh + 16;
                            if (type == 0 || type == 2)
                            {
                                // 880x600 暂停画面中验证的普通/路障贴图包络。
                                // 命中框的左沿比可见身体更靠左，路障帽比身体高约 24 像素。
                                int topPadding = type == 2 ? 26 : 6;
                                bx = imgX + hx + 14;
                                by = imgY + hy - topPadding;
                                bw = hw + 38;
                                bh = hh + topPadding + 6;
                            }
                            if (bx < -400 || bx > CanvasWidth + 500) continue;
                            if (by < -500 || by > CanvasHeight + 300) continue;

                            // 固定到 10Hz 的随机采样，避免每帧乱闪；同一帧重绘保持稳定。
                            if (VideoSeconds >= 15 && VideoSeconds < 21)
                            {
                                int tick = (int)((VideoSeconds - 15) * 10);
                                Random random = new Random(unchecked(tick * 7919 + i * 104729));
                                double severity = Math.Min(1, (VideoSeconds - 15) / 6);
                                if (random.NextDouble() < 0.12 + severity * 0.25) continue;
                                if (VideoSeconds >= 18 && random.NextDouble() < 0.5 + severity * 0.5)
                                {
                                    bw = random.Next(45, 110);
                                    bh = random.Next(80, 155);
                                    bx = random.Next(45, (int)CanvasWidth - bw - 10);
                                    by = random.Next(110, (int)CanvasHeight - bh - 25);
                                }
                                else
                                {
                                    int jitter = 2 + (int)(severity * 20);
                                    bx += random.Next(-jitter, jitter + 1);
                                    by += random.Next(-jitter, jitter + 1);
                                }
                            }

                            DrawZombie(g, bx, by, bw, bh, type, total, totalMax, armored);
                            drawn++;
                        }
                    }
                }

                string info = "僵尸 " + zLive + " (可见 " + drawn + ")   波次 " + wave + "/" + waveMax
                              + "   阳光 " + sun + "   " + fps.ToString("0.0") + "fps";
                float infoY = CanvasHeight - sUi.GetHeight(g) - 4f;
                Text(g, sUi, info, 10, infoY, C_UI);
            }
            finally
            {
                g.Restore(state);
            }
        }

        private static void DrawZombie(Graphics g, int x, int y, int w, int h,
                                       int type, int hp, int hpMax, bool armored)
        {
            Color box = armored ? C_ARMOR : C_LIVE;

            using (Pen ray = new Pen(box, 1f))
            {
                g.DrawLine(ray, CanvasWidth / 2f, 0f, x + w / 2f, y + h / 2f);
            }

            using (Pen pen = new Pen(box, 2f))
            {
                g.DrawRectangle(pen, x, y, w, h);
            }

            int barW = w < 46 ? 46 : w;
            int barH = 5;
            int barY = y - 9;
            if (barY < 2) barY = y + 2;

            using (SolidBrush bg = new SolidBrush(C_HP_BG))
            {
                g.FillRectangle(bg, x, barY, barW, barH);
            }

            float frac = (float)hp / (float)hpMax;
            if (frac < 0f) frac = 0f;
            if (frac > 1f) frac = 1f;
            int fillW = (int)(barW * frac);
            if (fillW > 0)
            {
                Color fc;
                if (frac > 0.5f) fc = Color.FromArgb(40, 220, 40);
                else if (frac > 0.22f) fc = Color.FromArgb(240, 200, 0);
                else fc = Color.FromArgb(240, 40, 40);
                using (SolidBrush fb = new SolidBrush(fc))
                {
                    g.FillRectangle(fb, x, barY, fillW, barH);
                }
            }

            Text(g, sSmall, "Z" + type + " " + hp, x, barY - 15, box);
        }

        private static void Text(Graphics g, Font f, string s, float x, float y, Color c)
        {
            using (SolidBrush shadow = new SolidBrush(C_OUTLINE))
            {
                g.DrawString(s, f, shadow, x + 1f, y + 1f);
            }
            using (SolidBrush b = new SolidBrush(c))
            {
                g.DrawString(s, f, b, x, y);
            }
        }
    }
}
