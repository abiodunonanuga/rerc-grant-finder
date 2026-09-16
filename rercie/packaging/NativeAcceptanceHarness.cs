using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;

namespace RERCeDesktop
{
    internal sealed class ControlEvidence
    {
        public string type { get; set; }
        public string text { get; set; }
        public string accessible_name { get; set; }
        public string accessible_description { get; set; }
        public string accessible_role { get; set; }
        public bool enabled { get; set; }
        public bool visible { get; set; }
        public bool tab_stop { get; set; }
        public int tab_index { get; set; }
        public int x { get; set; }
        public int y { get; set; }
        public int width { get; set; }
        public int height { get; set; }
        public bool text_clipped { get; set; }
        public bool outside_parent { get; set; }
    }

    internal static class AcceptanceProgram
    {
        [DllImport("shcore.dll")]
        private static extern int GetProcessDpiAwareness(IntPtr process, out int awareness);

        [DllImport("user32.dll")]
        private static extern uint GetDpiForWindow(IntPtr window);

        [DllImport("user32.dll")]
        private static extern bool PrintWindow(IntPtr window, IntPtr targetDeviceContext, uint flags);

        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

        private static IEnumerable<Control> Descendants(Control root)
        {
            foreach (Control child in root.Controls)
            {
                yield return child;
                foreach (Control descendant in Descendants(child)) yield return descendant;
            }
        }

        private static bool IsInteractive(Control control)
        {
            return control is Button || control is LinkLabel || control is TextBoxBase || control is ComboBox;
        }

        private static bool TextIsClipped(Control control)
        {
            if (string.IsNullOrWhiteSpace(control.Text) || control is RichTextBox || control is TextBoxBase || control is Panel || control is PictureBox || control is ProgressBar)
                return false;
            Size available = new Size(Math.Max(1, control.ClientSize.Width - 8), int.MaxValue);
            TextFormatFlags flags = control is Button || control is LinkLabel ? TextFormatFlags.SingleLine : TextFormatFlags.WordBreak;
            Size required = TextRenderer.MeasureText(control.Text.Replace("&", ""), control.Font, available, flags);
            return required.Width > control.ClientSize.Width + 1 || required.Height > control.ClientSize.Height + 1;
        }

        private static List<ControlEvidence> Inspect(MainForm form)
        {
            List<ControlEvidence> result = new List<ControlEvidence>();
            foreach (Control control in Descendants(form))
            {
                Rectangle bounds = control.Bounds;
                Size parentSize = control.Parent == null ? form.ClientSize : control.Parent.ClientSize;
                bool outsideParent = bounds.Left < 0 || bounds.Top < 0 || bounds.Right > parentSize.Width + 1 || bounds.Bottom > parentSize.Height + 1;
                ScrollableControl scrollableParent = control.Parent as ScrollableControl;
                if (outsideParent && scrollableParent != null && scrollableParent.AutoScroll) outsideParent = false;
                string accessibleName = "";
                string accessibleDescription = "";
                string accessibleRole = "";
                try
                {
                    accessibleName = control.AccessibilityObject.Name ?? "";
                    accessibleDescription = control.AccessibilityObject.Description ?? "";
                    accessibleRole = control.AccessibilityObject.Role.ToString();
                }
                catch { }
                result.Add(new ControlEvidence
                {
                    type = control.GetType().Name,
                    text = (control.Text ?? "").Replace("&", ""),
                    accessible_name = accessibleName,
                    accessible_description = accessibleDescription,
                    accessible_role = accessibleRole,
                    enabled = control.Enabled,
                    visible = control.Visible,
                    tab_stop = control.TabStop,
                    tab_index = control.TabIndex,
                    x = bounds.X,
                    y = bounds.Y,
                    width = bounds.Width,
                    height = bounds.Height,
                    text_clipped = control.Visible && TextIsClipped(control),
                    outside_parent = control.Visible && outsideParent,
                });
            }
            return result;
        }

        private static object Summarize(MainForm form, string scaleLabel, bool simulated, int evaluatedDpi)
        {
            List<ControlEvidence> controls = Inspect(form);
            List<ControlEvidence> interactive = controls.Where(control => control.visible && IsInteractiveName(control.type)).ToList();
            bool pass = !controls.Any(control => control.visible && (control.text_clipped || control.outside_parent))
                && !interactive.Any(control => control.tab_stop && string.IsNullOrWhiteSpace(control.accessible_name))
                && controls.Any(control => control.visible && control.type == "Button" && control.text == "Download and start" && !control.text_clipped);
            return new
            {
                scale = scaleLabel,
                simulated,
                pass,
                client_width = form.ClientSize.Width,
                client_height = form.ClientSize.Height,
                window_width = form.Width,
                window_height = form.Height,
                device_dpi = GetDpiForWindow(form.Handle),
                evaluated_dpi = evaluatedDpi,
                auto_scroll = form.AutoScroll,
                horizontal_scroll_visible = form.HorizontalScroll.Visible,
                vertical_scroll_visible = form.VerticalScroll.Visible,
                display_width = form.DisplayRectangle.Width,
                display_height = form.DisplayRectangle.Height,
                controls,
                clipped_text = controls.Where(control => control.text_clipped).Select(control => control.type + ":" + control.text).ToArray(),
                outside_parent = controls.Where(control => control.outside_parent).Select(control => control.type + ":" + control.text).ToArray(),
                unnamed_interactive = interactive.Where(control => string.IsNullOrWhiteSpace(control.accessible_name)).Select(control => control.type + ":" + control.text).ToArray(),
                tab_order = interactive.Where(control => control.tab_stop).OrderBy(control => control.tab_index).Select(control => control.accessible_name).ToArray(),
                download_button = controls.Where(control => control.type == "Button" && control.text == "Download and start").Select(control => new { control.width, control.height, control.text_clipped }).FirstOrDefault(),
            };
        }

        private static bool IsInteractiveName(string type)
        {
            return type == "Button" || type == "LinkLabel" || type == "TextBox" || type == "RichTextBox" || type == "ComboBox";
        }

        private static bool SummaryPass(object summary)
        {
            object value = summary.GetType().GetProperty("pass").GetValue(summary, null);
            return value is bool && (bool)value;
        }

        private static void CaptureControl(Control control, string path)
        {
            using (Bitmap image = new Bitmap(control.Width, control.Height))
            {
                control.DrawToBitmap(image, new Rectangle(Point.Empty, image.Size));
                image.Save(path, System.Drawing.Imaging.ImageFormat.Png);
            }
        }

        private static Bitmap RenderWindow(Form form)
        {
            Application.DoEvents();
            Bitmap image = new Bitmap(form.Width, form.Height);
            using (Graphics graphics = Graphics.FromImage(image))
            {
                IntPtr target = graphics.GetHdc();
                bool rendered;
                try { rendered = PrintWindow(form.Handle, target, 2); }
                finally { graphics.ReleaseHdc(target); }
                if (!rendered) form.DrawToBitmap(image, new Rectangle(Point.Empty, image.Size));
            }
            return image;
        }

        private static void CaptureWindow(Form form, string path)
        {
            using (Bitmap image = RenderWindow(form)) image.Save(path, System.Drawing.Imaging.ImageFormat.Png);
        }

        private static void CaptureWindowWithWebView(Form form, Control webView, string previewPath, string path)
        {
            using (Bitmap image = RenderWindow(form))
            using (Image preview = Image.FromFile(previewPath))
            using (Graphics graphics = Graphics.FromImage(image))
            {
                Point windowScreen = form.Location;
                Point viewScreen = webView.PointToScreen(Point.Empty);
                Rectangle viewBounds = new Rectangle(viewScreen.X - windowScreen.X, viewScreen.Y - windowScreen.Y, webView.Width, webView.Height);
                graphics.DrawImage(preview, viewBounds);
                image.Save(path, System.Drawing.Imaging.ImageFormat.Png);
            }
        }

        private static object SimulateScale(float factor, string label, string outputDirectory)
        {
            using (MainForm form = new MainForm(false))
            {
                form.StartPosition = FormStartPosition.Manual;
                form.ShowInTaskbar = false;
                form.Location = new Point(SystemInformation.VirtualScreen.Left - form.Width - 100, SystemInformation.VirtualScreen.Top - form.Height - 100);
                form.Show();
                Application.DoEvents();
                form.PrepareAcceptanceSetup();
                float currentFactor = Math.Max(1f, GetDpiForWindow(form.Handle) / 96f);
                float scaleFactor = factor / currentFactor;
                Dictionary<Control, Font> originalFonts = new Dictionary<Control, Font>();
                foreach (Control control in new[] { form }.Concat(Descendants(form)))
                    if (control.Font != null) originalFonts[control] = (Font)control.Font.Clone();
                form.SuspendLayout();
                form.Scale(new SizeF(scaleFactor, scaleFactor));
                foreach (KeyValuePair<Control, Font> entry in originalFonts)
                    entry.Key.Font = new Font(entry.Value.FontFamily, entry.Value.SizeInPoints * scaleFactor, entry.Value.Style, GraphicsUnit.Point);
                form.ResumeLayout(true);
                foreach (Font font in originalFonts.Values) font.Dispose();
                form.PerformLayout();
                Application.DoEvents();
                CaptureControl(form, Path.Combine(outputDirectory, "setup-" + label.Replace("%", "") + "-simulated.png"));
                object summary = Summarize(form, label, true, (int)Math.Round(factor * 96));
                if (form.VerticalScroll.Visible)
                {
                    form.AutoScrollPosition = new Point(0, form.DisplayRectangle.Height);
                    Application.DoEvents();
                    CaptureControl(form, Path.Combine(outputDirectory, "setup-" + label.Replace("%", "") + "-simulated-bottom.png"));
                }
                form.Hide();
                return summary;
            }
        }

        [STAThread]
        private static int Main(string[] args)
        {
            if (args.Length < 2)
            {
                Console.Error.WriteLine("Usage: RERC-e.exe <app-url> <output-directory>");
                return 2;
            }
            string address = args[0];
            string outputDirectory = Path.GetFullPath(args[1]);
            Directory.CreateDirectory(outputDirectory);
            DpiAwareness.Initialize();
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            MainForm form = new MainForm(false);
            form.StartPosition = FormStartPosition.Manual;
            form.ShowInTaskbar = false;
            form.Location = new Point(SystemInformation.VirtualScreen.Left - form.Width - 100, SystemInformation.VirtualScreen.Top - form.Height - 100);
            int exitCode = 1;
            string progressPath = Path.Combine(outputDirectory, "acceptance-progress.txt");
            form.AcceptanceProgress = delegate(string stage)
            {
                File.AppendAllText(progressPath, stage + Environment.NewLine, new UTF8Encoding(false));
            };
            form.Shown += async delegate
            {
                try
                {
                    File.AppendAllText(progressPath, "setup" + Environment.NewLine, new UTF8Encoding(false));
                    form.PrepareAcceptanceSetup();
                    await Task.Delay(250);
                    CaptureWindow(form, Path.Combine(outputDirectory, "setup-current-dpi.png"));
                    object current = Summarize(form, "current", false, (int)GetDpiForWindow(form.Handle));
                    List<ControlEvidence> currentControls = Inspect(form);
                    File.AppendAllText(progressPath, "geometry" + Environment.NewLine, new UTF8Encoding(false));
                    object scale100 = SimulateScale(1.0f, "100%", outputDirectory);
                    object scale150 = SimulateScale(1.5f, "150%", outputDirectory);
                    object scale200 = SimulateScale(2.0f, "200%", outputDirectory);
                    bool geometryPass = SummaryPass(scale100) && SummaryPass(scale150) && SummaryPass(scale200);

                    File.AppendAllText(progressPath, "webview" + Environment.NewLine, new UTF8Encoding(false));
                    string profile = Path.Combine(outputDirectory, "webview-profile");
                    string dom = await form.OpenAcceptanceAppAsync(address, profile);
                    await Task.Delay(750);
                    bool embeddedContentVisible = form.AcceptanceWebView.Visible && form.AcceptanceWebView.Width > 0 && form.AcceptanceWebView.Height > 0;
                    string webViewImage = Path.Combine(outputDirectory, "embedded-rerc-e.png");
                    using (FileStream stream = new FileStream(webViewImage, FileMode.Create, FileAccess.Write, FileShare.None))
                        await form.AcceptanceWebView.CoreWebView2.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png, stream);
                    CaptureWindowWithWebView(form, form.AcceptanceWebView, webViewImage, Path.Combine(outputDirectory, "native-shell-with-webview.png"));

                    int dpiAwareness;
                    int awarenessCall = GetProcessDpiAwareness(IntPtr.Zero, out dpiAwareness);
                    bool perMonitorDpiAware = awarenessCall == 0 && dpiAwareness == 2;
                    string decodedDom = Json.DeserializeObject(dom) as string;
                    Dictionary<string, object> embeddedDom = string.IsNullOrWhiteSpace(decodedDom)
                        ? new Dictionary<string, object>()
                        : Json.Deserialize<Dictionary<string, object>>(decodedDom);
                    bool embeddedPass = embeddedDom.ContainsKey("projectVisible")
                        && Convert.ToBoolean(embeddedDom["projectVisible"])
                        && embeddedDom.ContainsKey("stepCount")
                        && Convert.ToInt32(embeddedDom["stepCount"]) == 3
                        && embeddedDom.ContainsKey("tokenStored")
                        && Convert.ToBoolean(embeddedDom["tokenStored"])
                        && embeddedDom.ContainsKey("pageOverflow")
                        && !Convert.ToBoolean(embeddedDom["pageOverflow"])
                        && embeddedDom.ContainsKey("nativeHost")
                        && Convert.ToBoolean(embeddedDom["nativeHost"])
                        && embeddedDom.ContainsKey("mascotAnimation")
                        && string.Equals(Convert.ToString(embeddedDom["mascotAnimation"]), "none", StringComparison.OrdinalIgnoreCase);
                    bool nativePass = !currentControls.Any(control => control.visible && (control.text_clipped || control.outside_parent))
                        && currentControls.Any(control => control.visible && control.type == "Button" && control.text == "Download and start" && !control.text_clipped)
                        && !currentControls.Any(control => control.visible && control.tab_stop && IsInteractiveName(control.type) && string.IsNullOrWhiteSpace(control.accessible_name));
                    object report = new
                    {
                        status = perMonitorDpiAware && nativePass && geometryPass && embeddedPass && embeddedContentVisible ? "PASS" : "FAIL",
                        app = "RERC-e",
                        version = Config.Version,
                        os = Environment.OSVersion.VersionString,
                        clr = Environment.Version.ToString(),
                        process_dpi_awareness = dpiAwareness,
                        process_dpi_awareness_call = awarenessCall,
                        per_monitor_dpi_aware = perMonitorDpiAware,
                        native_layout_pass = nativePass,
                        simulated_geometry_pass = geometryPass,
                        embedded_app_pass = embeddedPass,
                        embedded_content_visible = embeddedContentVisible,
                        current,
                        geometry = new[] { scale100, scale150, scale200 },
                        embedded = new
                        {
                            url = address,
                            dom = embeddedDom,
                            screenshot = Path.GetFileName(webViewImage),
                            webview_runtime = CoreWebView2Environment.GetAvailableBrowserVersionString(),
                        },
                    };
                    File.WriteAllText(Path.Combine(outputDirectory, "native-acceptance.json"), Json.Serialize(report), new UTF8Encoding(false));
                    File.AppendAllText(progressPath, "complete" + Environment.NewLine, new UTF8Encoding(false));
                    exitCode = 0;
                }
                catch (Exception error)
                {
                    File.WriteAllText(Path.Combine(outputDirectory, "native-acceptance.json"), Json.Serialize(new { status = "FAIL", error = error.ToString() }), new UTF8Encoding(false));
                }
                finally
                {
                    form.Close();
                }
            };
            Application.Run(form);
            return exitCode;
        }
    }
}
