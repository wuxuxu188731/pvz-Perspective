using System;
using System.Drawing;
using System.Drawing.Drawing2D;

namespace PvzEsp
{
    // 仅用于录屏的演出画面，不关闭或写入游戏。
    internal static class VideoEnding
    {
        public static readonly Rectangle Button = new Rectangle(350, 367, 180, 48);

        public static void Draw(Graphics g, Size size, Image frozenFrame, bool showDialog)
        {
            GraphicsState state = g.Save();
            try
            {
                g.ScaleTransform(size.Width / 880f, size.Height / 600f);
                if (frozenFrame != null) g.DrawImage(frozenFrame, 0, 0, 880, 600);
                else g.Clear(Color.FromArgb(35, 39, 34));
                using (Brush dim = new SolidBrush(Color.FromArgb(135, 0, 0, 0)))
                    g.FillRectangle(dim, 0, 0, 880, 600);
                if (!showDialog) return;

                g.SmoothingMode = SmoothingMode.AntiAlias;
                using (Brush shadow = new SolidBrush(Color.FromArgb(100, 0, 0, 0)))
                    g.FillRectangle(shadow, 193, 187, 510, 260);
                Rectangle panel = new Rectangle(185, 175, 510, 260);
                using (Brush stone = new LinearGradientBrush(panel, Color.FromArgb(105, 108, 125), Color.FromArgb(55, 57, 70), 90f))
                    g.FillRectangle(stone, panel);
                using (Pen edge = new Pen(Color.FromArgb(35, 36, 46), 6))
                    g.DrawRectangle(edge, panel);
                using (Pen bevel = new Pen(Color.FromArgb(157, 159, 175), 2))
                    g.DrawRectangle(bevel, 191, 181, 498, 248);
                using (Pen divider = new Pen(Color.FromArgb(44, 46, 57), 2))
                    g.DrawLine(divider, 215, 241, 665, 241);

                using (Font title = new Font("Microsoft YaHei", 22, FontStyle.Bold))
                using (Font body = new Font("Microsoft YaHei", 13, FontStyle.Bold))
                using (Font small = new Font("Consolas", 10))
                using (StringFormat center = new StringFormat())
                {
                    center.Alignment = StringAlignment.Center;
                    center.LineAlignment = StringAlignment.Center;
                    Label(g, title, "连接已断开", new RectangleF(200, 190, 480, 44), Color.FromArgb(235, 224, 190), center);
                    Label(g, body, "检测到当前您的游戏环境存在异常，\n您已被踢下线。", new RectangleF(210, 257, 460, 68), Color.FromArgb(242, 238, 222), center);
                    Label(g, small, "错误代码：1051", new RectangleF(210, 331, 460, 24), Color.FromArgb(180, 183, 192), center);
                    using (Brush button = new LinearGradientBrush(Button, Color.FromArgb(118, 124, 139), Color.FromArgb(69, 73, 88), 90f))
                        g.FillRectangle(button, Button);
                    using (Pen edge = new Pen(Color.FromArgb(30, 33, 42), 3))
                        g.DrawRectangle(edge, Button);
                    using (Pen light = new Pen(Color.FromArgb(165, 169, 185), 1))
                        g.DrawRectangle(light, 353, 370, 174, 42);
                    Label(g, body, "确 定", Button, Color.FromArgb(90, 255, 20), center);
                }
            }
            finally { g.Restore(state); }
        }

        private static void Label(Graphics g, Font font, string text, RectangleF bounds, Color color, StringFormat format)
        {
            RectangleF shadow = bounds;
            shadow.Offset(1, 2);
            using (Brush brush = new SolidBrush(Color.FromArgb(25, 26, 30)))
                g.DrawString(text, font, brush, shadow, format);
            using (Brush brush = new SolidBrush(color))
                g.DrawString(text, font, brush, bounds, format);
        }
    }
}
