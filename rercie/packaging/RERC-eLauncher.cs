using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace RERCeDesktop
{
    internal static class DpiAwareness
    {
        private static readonly IntPtr PerMonitorV2 = new IntPtr(-4);

        [DllImport("user32.dll", EntryPoint = "SetProcessDpiAwarenessContext", SetLastError = true)]
        private static extern bool SetProcessDpiAwarenessContext(IntPtr value);

        [DllImport("shcore.dll")]
        private static extern int SetProcessDpiAwareness(int value);

        [DllImport("user32.dll")]
        private static extern bool SetProcessDPIAware();

        [DllImport("user32.dll")]
        private static extern uint GetDpiForWindow(IntPtr window);

        internal static void Initialize()
        {
            try
            {
                if (SetProcessDpiAwarenessContext(PerMonitorV2)) return;
            }
            catch (EntryPointNotFoundException) { }
            catch (DllNotFoundException) { }

            try
            {
                if (SetProcessDpiAwareness(2) == 0) return;
            }
            catch (EntryPointNotFoundException) { }
            catch (DllNotFoundException) { }

            try { SetProcessDPIAware(); }
            catch (EntryPointNotFoundException) { }
            catch (DllNotFoundException) { }
        }

        internal static int WindowDpi(Control control)
        {
            try
            {
                if (control != null && control.IsHandleCreated)
                {
                    uint dpi = GetDpiForWindow(control.Handle);
                    if (dpi >= 96) return (int)dpi;
                }
            }
            catch (EntryPointNotFoundException) { }
            catch (DllNotFoundException) { }
            return 96;
        }
    }

    internal static class Config
    {
        public const string Version = "0.5.1";
        public const string AppUrl = "http://127.0.0.1:8789";
        public const string AppHealthUrl = AppUrl + "/health";
        public const string ModelHealthUrl = "http://127.0.0.1:8788/health";
        public const string ModelListUrl = "http://127.0.0.1:8788/v1/models";
        public const string ModelName = "gemma-3-1b-it-Q4_K_M.gguf";
        public const string ModelUrl = "https://huggingface.co/ggml-org/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf?download=true";
        public const long ModelBytes = 806058240L;
        public const string ModelSha256 = "8ccc5cd1f1b3602548715ae25a66ed73fd5dc68a210412eea643eb20eb75a135";
        public const string VcRuntimeUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe";
        public const string ModelPageUrl = "https://huggingface.co/ggml-org/gemma-3-1b-it-GGUF";
        public const string ModelLicenseUrl = "https://ai.google.dev/gemma/terms";
        public const int MaxPlanBytes = 256 * 1024;
        public const string PlanSchema = "rerc-e-handoff";
        public const string LegacyPlanSchema = "rercie-handoff";
        public const int PlanVersion = 1;
    }

    internal sealed class IntegrityEntry
    {
        public string path { get; set; }
        public long bytes { get; set; }
        public string sha256 { get; set; }
    }

    internal sealed class IntegrityManifest
    {
        public List<IntegrityEntry> files { get; set; }
    }

    internal sealed class ProcessRecord
    {
        public int pid { get; set; }
        public string executable_path { get; set; }
        public string start_time_utc { get; set; }
        public string session_token { get; set; }
    }

    internal static class Runtime
    {
        public static readonly string Root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
        public static readonly string ModelsDir = Path.Combine(Root, "models");
        public static readonly string ModelPath = Path.Combine(ModelsDir, Config.ModelName);
        public static readonly string RuntimeDir = Path.Combine(Root, "runtime");
        public static readonly string LlamaDir = Path.Combine(RuntimeDir, "llama");
        public static readonly string LlamaExe = Path.Combine(LlamaDir, "llama-server.exe");
        public static readonly string ServiceDir = Path.Combine(Root, "service");
        public static readonly string ServiceExe = Path.Combine(ServiceDir, "RERC-eService.exe");
        public static readonly string PidDir = Path.Combine(RuntimeDir, "pids");
        public static readonly string HandoffDir = Path.Combine(RuntimeDir, "handoff");
        public static readonly string PendingHandoffPath = Path.Combine(HandoffDir, "pending.rercie");
        public static readonly string IntegrityPath = Path.Combine(Root, "file_integrity.json");
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

        public static string Sha256(string path)
        {
            using (FileStream stream = File.OpenRead(path))
            using (SHA256 hash = SHA256.Create())
            {
                byte[] bytes = hash.ComputeHash(stream);
                StringBuilder output = new StringBuilder(bytes.Length * 2);
                foreach (byte value in bytes) output.Append(value.ToString("x2"));
                return output.ToString();
            }
        }

        public static void VerifyPackage()
        {
            if (!File.Exists(IntegrityPath)) throw new InvalidOperationException("RERC-e is missing its safety file. Run the installer again.");
            IntegrityManifest manifest = Json.Deserialize<IntegrityManifest>(File.ReadAllText(IntegrityPath));
            if (manifest == null || manifest.files == null || manifest.files.Count == 0) throw new InvalidOperationException("RERC-e's safety file is not valid. Run the installer again.");
            foreach (IntegrityEntry entry in manifest.files)
            {
                string relative = (entry.path ?? "").Replace('/', Path.DirectorySeparatorChar);
                string fullPath = Path.GetFullPath(Path.Combine(Root, relative));
                if (!fullPath.StartsWith(Root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("RERC-e's safety file has an invalid path.");
                FileInfo file = new FileInfo(fullPath);
                if (!file.Exists || file.Length != entry.bytes || !string.Equals(Sha256(fullPath), entry.sha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("A RERC-e file did not pass its safety check: " + relative + ". Run the installer again.");
            }
        }

        public static void StagePlanFile(string sourcePath)
        {
            if (string.IsNullOrWhiteSpace(sourcePath)) throw new InvalidOperationException("Choose a Community Explorer plan first.");
            string fullPath = Path.GetFullPath(sourcePath);
            string extension = Path.GetExtension(fullPath);
            if (!string.Equals(extension, ".rerc-e", StringComparison.OrdinalIgnoreCase)
                && !string.Equals(extension, ".rercie", StringComparison.OrdinalIgnoreCase)
                && !string.Equals(extension, ".json", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Choose a RERC-e Community Explorer plan file.");
            FileInfo source = new FileInfo(fullPath);
            if (!source.Exists || source.Length <= 0 || source.Length > Config.MaxPlanBytes)
                throw new InvalidOperationException("The Community Explorer plan must be a non-empty file no larger than 256 KB.");
            byte[] bytes = File.ReadAllBytes(fullPath);
            if (bytes.Length <= 0 || bytes.Length > Config.MaxPlanBytes)
                throw new InvalidOperationException("The Community Explorer plan must be a non-empty file no larger than 256 KB.");
            string text;
            try
            {
                text = new UTF8Encoding(false, true).GetString(bytes);
                if (text.Length > 0 && text[0] == '\ufeff') text = text.Substring(1);
            }
            catch (DecoderFallbackException)
            {
                throw new InvalidOperationException("The Community Explorer plan must be UTF-8 JSON text.");
            }
            IDictionary<string, object> plan;
            try { plan = Json.DeserializeObject(text) as IDictionary<string, object>; }
            catch { plan = null; }
            object schema;
            object version;
            int parsedVersion;
            if (plan == null
                || !plan.TryGetValue("schema", out schema)
                || !(string.Equals(Convert.ToString(schema), Config.PlanSchema, StringComparison.Ordinal)
                     || string.Equals(Convert.ToString(schema), Config.LegacyPlanSchema, StringComparison.Ordinal))
                || !plan.TryGetValue("version", out version)
                || !int.TryParse(Convert.ToString(version), out parsedVersion)
                || parsedVersion != Config.PlanVersion)
                throw new InvalidOperationException("This is not a supported RERC-e Community Explorer plan.");

            Directory.CreateDirectory(HandoffDir);
            string temporaryPath = Path.Combine(HandoffDir, Guid.NewGuid().ToString("N") + ".tmp");
            try
            {
                File.WriteAllBytes(temporaryPath, bytes);
                if (File.Exists(PendingHandoffPath)) File.Delete(PendingHandoffPath);
                File.Move(temporaryPath, PendingHandoffPath);
            }
            finally
            {
                try { if (File.Exists(temporaryPath)) File.Delete(temporaryPath); } catch { }
            }
        }

        public static bool ModelReady()
        {
            FileInfo file = new FileInfo(ModelPath);
            return file.Exists && file.Length == Config.ModelBytes && string.Equals(Sha256(ModelPath), Config.ModelSha256, StringComparison.OrdinalIgnoreCase);
        }

        public static bool VcRuntimeReady()
        {
            string system = Environment.GetFolderPath(Environment.SpecialFolder.System);
            string[] names = { "MSVCP140.dll", "VCRUNTIME140.dll", "VCRUNTIME140_1.dll" };
            foreach (string name in names) if (!File.Exists(Path.Combine(system, name))) return false;
            return true;
        }

        public static bool PortInUse(int port)
        {
            using (TcpClient client = new TcpClient())
            {
                try
                {
                    IAsyncResult attempt = client.BeginConnect("127.0.0.1", port, null, null);
                    if (!attempt.AsyncWaitHandle.WaitOne(600)) return false;
                    client.EndConnect(attempt);
                    return true;
                }
                catch { return false; }
            }
        }

        private static bool TryGetOwnedProcess(string name, string expectedExecutable, out ProcessRecord record, out Process process)
        {
            record = null;
            process = null;
            string recordPath = Path.Combine(PidDir, name + ".json");
            if (!File.Exists(recordPath)) return false;
            try
            {
                record = Json.Deserialize<ProcessRecord>(File.ReadAllText(recordPath));
                if (record == null || record.pid <= 0 || string.IsNullOrWhiteSpace(record.executable_path) || string.IsNullOrWhiteSpace(record.start_time_utc)) return false;
                process = Process.GetProcessById(record.pid);
                if (process.HasExited) return false;
                string actualPath = process.MainModule.FileName;
                DateTime actualStart = process.StartTime.ToUniversalTime();
                DateTime recordedStart = DateTime.Parse(record.start_time_utc).ToUniversalTime();
                return string.Equals(Path.GetFullPath(actualPath), Path.GetFullPath(expectedExecutable), StringComparison.OrdinalIgnoreCase)
                    && string.Equals(Path.GetFullPath(record.executable_path), Path.GetFullPath(expectedExecutable), StringComparison.OrdinalIgnoreCase)
                    && Math.Abs((actualStart - recordedStart).TotalSeconds) < 3;
            }
            catch { return false; }
        }

        public static bool AppReady()
        {
            ProcessRecord record;
            Process process;
            return TryGetOwnedProcess("app", ServiceExe, out record, out process)
                && !string.IsNullOrWhiteSpace(record.session_token)
                && EndpointContains(Config.AppHealthUrl, "\"app\": \"RERC-e\"", record.session_token);
        }

        public static bool ModelServerReady()
        {
            ProcessRecord record;
            Process process;
            return TryGetOwnedProcess("llama", LlamaExe, out record, out process)
                && EndpointContains(Config.ModelHealthUrl, "ok", null)
                && EndpointContains(Config.ModelListUrl, Config.ModelName, null);
        }

        public static string AppBrowserUrl()
        {
            ProcessRecord record;
            Process process;
            if (!TryGetOwnedProcess("app", ServiceExe, out record, out process) || string.IsNullOrWhiteSpace(record.session_token))
                throw new InvalidOperationException("RERC-e's local session is not ready. Start RERC-e again.");
            return Config.AppUrl + "/#token=" + Uri.EscapeDataString(record.session_token);
        }

        public static string CreateSessionToken()
        {
            byte[] bytes = new byte[32];
            using (RandomNumberGenerator generator = RandomNumberGenerator.Create()) generator.GetBytes(bytes);
            StringBuilder token = new StringBuilder(64);
            foreach (byte value in bytes) token.Append(value.ToString("x2"));
            return token.ToString();
        }

        private static bool EndpointContains(string url, string expected, string sessionToken)
        {
            try
            {
                HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
                request.Timeout = 1800;
                request.ReadWriteTimeout = 1800;
                request.Proxy = null;
                if (!string.IsNullOrWhiteSpace(sessionToken)) request.Headers["X-RERC-e-Token"] = sessionToken;
                using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
                using (StreamReader reader = new StreamReader(response.GetResponseStream()))
                    return reader.ReadToEnd().IndexOf(expected, StringComparison.OrdinalIgnoreCase) >= 0;
            }
            catch { return false; }
        }
        public static async Task WaitForAsync(Func<bool> check, int seconds, string message)
        {
            for (int i = 0; i < seconds * 2; i++)
            {
                if (check()) return;
                await Task.Delay(500);
            }
            throw new InvalidOperationException(message);
        }

        public static Process StartHidden(string name, string executable, string arguments, string workingDirectory, IDictionary<string, string> environment, string sessionToken)
        {
            ProcessStartInfo info = new ProcessStartInfo(executable, arguments);
            info.WorkingDirectory = workingDirectory;
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.WindowStyle = ProcessWindowStyle.Hidden;
            if (environment != null)
                foreach (KeyValuePair<string, string> item in environment) info.EnvironmentVariables[item.Key] = item.Value;
            Process process = Process.Start(info);
            if (process == null) throw new InvalidOperationException("A part of RERC-e could not start. Restart RERC-e and try again.");
            WriteProcessRecord(name, process, executable, sessionToken);
            return process;
        }

        private static void WriteProcessRecord(string name, Process process, string executable, string sessionToken)
        {
            Directory.CreateDirectory(PidDir);
            process.Refresh();
            ProcessRecord record = new ProcessRecord
            {
                pid = process.Id,
                executable_path = Path.GetFullPath(executable),
                start_time_utc = process.StartTime.ToUniversalTime().ToString("o"),
                session_token = sessionToken
            };
            File.WriteAllText(Path.Combine(PidDir, name + ".json"), Json.Serialize(record), new UTF8Encoding(false));
        }
        public static int StopOwnedProcesses(out int failures)
        {
            int stopped = 0;
            failures = 0;
            foreach (string name in new[] { "app", "llama" })
            {
                string recordPath = Path.Combine(PidDir, name + ".json");
                if (!File.Exists(recordPath)) continue;
                try
                {
                    ProcessRecord record = Json.Deserialize<ProcessRecord>(File.ReadAllText(recordPath));
                    string expected = name == "app" ? ServiceExe : LlamaExe;
                    Process process;
                    ProcessRecord verified;
                    if (!TryGetOwnedProcess(name, expected, out verified, out process))
                    {
                        try { Process.GetProcessById(record.pid); failures++; }
                        catch (ArgumentException) { File.Delete(recordPath); }
                        continue;
                    }
                    process.Kill();
                    bool exited = process.WaitForExit(10000) && process.HasExited;
                    if (!exited) { failures++; continue; }
                    File.Delete(recordPath);
                    stopped++;
                }
                catch { failures++; }
            }
            return stopped;
        }
        public static void OpenBrowser(string url)
        {
            ProcessStartInfo info = new ProcessStartInfo(url);
            info.UseShellExecute = true;
            Process.Start(info);
        }

        public static void EnsureDownloadSpace(string destination, long expectedBytes)
        {
            string partial = destination + ".partial";
            long existing = File.Exists(partial) ? new FileInfo(partial).Length : 0L;
            long remaining = Math.Max(0L, expectedBytes - existing);
            string root = Path.GetPathRoot(Path.GetFullPath(destination));
            DriveInfo drive = new DriveInfo(root);
            long reserve = 200L * 1024L * 1024L;
            if (drive.AvailableFreeSpace < remaining + reserve)
                throw new InvalidOperationException("RERC-e needs about " + ((remaining + reserve) / 1048576L).ToString("N0") + " MB of free space before downloading.");
        }


        public static async Task DownloadAsync(string url, string destination, Action<long, long> progress, CancellationToken cancellationToken)
        {
            bool isModelDownload = string.Equals(url, Config.ModelUrl, StringComparison.OrdinalIgnoreCase);
            string downloadName = isModelDownload ? "Google Gemma" : "the required Microsoft Windows component";
            string partial = destination + ".partial";
            Directory.CreateDirectory(Path.GetDirectoryName(destination));
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            Exception lastError = null;
            for (int attempt = 1; attempt <= 4; attempt++)
            {
                try
                {
                    long existing = File.Exists(partial) ? new FileInfo(partial).Length : 0L;
                    if (existing < 0 || (isModelDownload && existing > Config.ModelBytes))
                    {
                        File.Delete(partial);
                        existing = 0L;
                    }
                    using (HttpClientHandler handler = new HttpClientHandler())
                    {
                        handler.AllowAutoRedirect = true;
                        handler.MaxAutomaticRedirections = 10;
                        handler.AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate;
                        handler.Proxy = WebRequest.DefaultWebProxy;
                        if (handler.Proxy != null) handler.Proxy.Credentials = CredentialCache.DefaultCredentials;
                        using (HttpClient client = new HttpClient(handler))
                        using (HttpRequestMessage request = new HttpRequestMessage(HttpMethod.Get, url))
                        {
                            client.Timeout = Timeout.InfiniteTimeSpan;
                            request.Headers.UserAgent.ParseAdd("RERC-e/" + Config.Version + " (Windows; local grant-writing guide)");
                            request.Headers.Accept.ParseAdd("application/octet-stream");
                            if (existing > 0) request.Headers.Range = new RangeHeaderValue(existing, null);
                            using (HttpResponseMessage response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken))
                            {
                                if (response.StatusCode == HttpStatusCode.RequestedRangeNotSatisfiable)
                                {
                                    File.Delete(partial);
                                    throw new IOException("The saved partial download could not be resumed.");
                                }
                                response.EnsureSuccessStatusCode();
                                bool resumed = existing > 0 && response.StatusCode == HttpStatusCode.PartialContent;
                                long offset = resumed ? existing : 0L;
                                long contentLength = response.Content.Headers.ContentLength.GetValueOrDefault();
                                long total = contentLength > 0 ? offset + contentLength : (isModelDownload ? Config.ModelBytes : 0L);
                                FileMode mode = resumed ? FileMode.Append : FileMode.Create;
                                using (Stream input = await response.Content.ReadAsStreamAsync())
                                using (FileStream output = new FileStream(partial, mode, FileAccess.Write, FileShare.None, 131072, true))
                                {
                                    byte[] buffer = new byte[131072];
                                    long done = offset;
                                    if (progress != null) progress(done, total);
                                    int read;
                                    while ((read = await input.ReadAsync(buffer, 0, buffer.Length, cancellationToken)) > 0)
                                    {
                                        await output.WriteAsync(buffer, 0, read, cancellationToken);
                                        done += read;
                                        if (progress != null) progress(done, total);
                                    }
                                }
                            }
                        }
                    }
                    if (File.Exists(destination)) File.Delete(destination);
                    File.Move(partial, destination);
                    return;
                }
                catch (OperationCanceledException)
                {
                    throw new InvalidOperationException("The download was canceled. The saved partial download can resume later.");
                }
                catch (Exception error)
                {
                    lastError = error;
                }
                if (attempt < 4) await Task.Delay(attempt * 1500, cancellationToken);
            }
            string detail = lastError == null ? "Unknown network error." : RootMessage(lastError);
            throw new InvalidOperationException("RERC-e could not download " + downloadName + ". Check your internet connection and try again. The saved partial download will resume. Details: " + detail, lastError);
        }

        private static string RootMessage(Exception error)
        {
            Exception current = error;
            while (current.InnerException != null) current = current.InnerException;
            return string.IsNullOrWhiteSpace(current.Message) ? error.GetType().Name : current.Message;
        }

        public static async Task<object> ProbeModelDownloadAsync()
        {
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            using (HttpClientHandler handler = new HttpClientHandler())
            {
                handler.AllowAutoRedirect = true;
                handler.MaxAutomaticRedirections = 10;
                handler.AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate;
                handler.Proxy = WebRequest.DefaultWebProxy;
                if (handler.Proxy != null) handler.Proxy.Credentials = CredentialCache.DefaultCredentials;
                using (HttpClient client = new HttpClient(handler))
                using (HttpRequestMessage request = new HttpRequestMessage(HttpMethod.Get, Config.ModelUrl))
                {
                    client.Timeout = TimeSpan.FromSeconds(45);
                    request.Headers.UserAgent.ParseAdd("RERC-e/" + Config.Version + " (Windows; download probe)");
                    request.Headers.Accept.ParseAdd("application/octet-stream");
                    request.Headers.Range = new RangeHeaderValue(0, 1023);
                    using (HttpResponseMessage response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead))
                    {
                        response.EnsureSuccessStatusCode();
                        byte[] body = new byte[1024];
                        int totalRead = 0;
                        using (Stream input = await response.Content.ReadAsStreamAsync())
                        {
                            while (totalRead < body.Length)
                            {
                                int read = await input.ReadAsync(body, totalRead, body.Length - totalRead);
                                if (read <= 0) break;
                                totalRead += read;
                            }
                        }
                        if (totalRead != 1024) throw new InvalidOperationException("The Gemma endpoint returned an unexpected probe size.");
                        return new { status = "PASS", http_status = (int)response.StatusCode, bytes = totalRead, model = Config.ModelName, source = Config.ModelPageUrl };
                    }
                }
            }
        }
    }

    internal sealed class AccessibleStatusLabel : Label
    {
        private int lastDownloadMilestone = -1;

        protected override void OnTextChanged(EventArgs e)
        {
            base.OnTextChanged(e);
            AccessibleDescription = Text;
            bool notify = true;
            const string prefix = "Downloading the local model... ";
            if ((Text ?? "").StartsWith(prefix, StringComparison.Ordinal))
            {
                int percentEnd = Text.IndexOf('%', prefix.Length);
                int percent;
                if (percentEnd > prefix.Length && int.TryParse(Text.Substring(prefix.Length, percentEnd - prefix.Length), out percent))
                {
                    int milestone = percent / 10;
                    notify = milestone != lastDownloadMilestone;
                    lastDownloadMilestone = milestone;
                }
            }
            else
            {
                lastDownloadMilestone = -1;
            }
            if (notify && IsHandleCreated)
                AccessibilityNotifyClients(AccessibleEvents.DescriptionChange, -1);
        }
    }

    internal sealed class MainForm : Form
    {
        private readonly AccessibleStatusLabel statusLabel = new AccessibleStatusLabel();
        private readonly ProgressBar progressBar = new ProgressBar();

        private readonly Button startButton = new Button();
        private readonly Button openButton = new Button();
        private readonly Button stopButton = new Button();
        private readonly Panel browserPanel = new Panel();
        private readonly WebView2 appView = new WebView2();
        private readonly Button setupButton = new Button();
        private CoreWebView2Environment appEnvironment;
        private bool viewConfigured;
        private bool webViewRuntimeInstallAttempted;
        private readonly bool startupPlanStaged;
        private bool busy;
        private CancellationTokenSource activeOperationCancellation;

        public MainForm(bool hasStartupPlan)
        {
            startupPlanStaged = hasStartupPlan;
            Text = "RERC-e";
            AutoScaleDimensions = new SizeF(96f, 96f);
            AutoScaleMode = AutoScaleMode.Dpi;
            ClientSize = new Size(760, 540);
            MinimumSize = new Size(776, 579);
            StartPosition = FormStartPosition.CenterScreen;
            AutoScroll = true;
            BackColor = Color.FromArgb(248, 249, 245);
            Font = new Font("Segoe UI", 9.5f);
            Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);

            Panel hero = new Panel();
            hero.Location = new Point(0, 0);
            hero.Size = new Size(760, 242);
            hero.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            hero.BackColor = Color.FromArgb(17, 67, 53);
            Controls.Add(hero);

            PictureBox picture = new PictureBox();
            picture.Location = new Point(570, 26);
            picture.Size = new Size(160, 186);
            picture.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            picture.SizeMode = PictureBoxSizeMode.Zoom;
            picture.AccessibleName = "RERC-e, a bald eagle field guide holding a notebook";
            picture.AccessibleDescription = "RERC-e is the outdoor guide character for this local grant-writing app.";
            string imagePath = Path.Combine(Runtime.Root, "assets", "rerc-e-eagle.jpg");
            if (File.Exists(imagePath)) picture.Image = Image.FromFile(imagePath);
            hero.Controls.Add(picture);

            Label brand = MakeLabel("Recreation Economy for Rural Communities", 32, 28, 525, 30, 10.5f, true, Color.White);
            Label title = MakeLabel("Meet RERC-e", 32, 75, 525, 50, 27f, true, Color.White);
            Label intro = MakeLabel("Your local guide from project idea to a grant draft.", 32, 135, 525, 36, 13f, false, Color.FromArgb(242, 248, 243));
            Label boundary = MakeLabel("Community-built by Timberwing Systems. RERC-e does not determine eligibility or submit an application.", 32, 183, 525, 48, 9.5f, false, Color.FromArgb(212, 228, 216));
            hero.Controls.Add(brand); hero.Controls.Add(title); hero.Controls.Add(intro); hero.Controls.Add(boundary);

            Panel accent = new Panel();
            accent.Location = new Point(0, 242);
            accent.Size = new Size(760, 4);
            accent.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            accent.BackColor = Color.FromArgb(222, 181, 97);
            Controls.Add(accent);

            Label modelNote = MakeLabel("First use: download Google Gemma (about 0.81 GB)", 32, 265, 696, 28, 11f, true, Color.FromArgb(23, 63, 53));
            Controls.Add(modelNote);

            LinkLabel modelLink = MakeLink("View the model page", 32, 324, 190, Config.ModelPageUrl);
            LinkLabel licenseLink = MakeLink("Read the Gemma Terms", 234, 324, 220, Config.ModelLicenseUrl);
            Controls.Add(modelLink); Controls.Add(licenseLink);

            Label licenseNote = MakeLabel("The model stays on this computer. Review the Gemma Terms before downloading.", 32, 296, 696, 28, 9.5f, false, Color.FromArgb(70, 80, 75));
            Controls.Add(licenseNote);

            Label setupHeading = MakeLabel("Setup and status", 32, 348, 696, 24, 11f, true, Color.FromArgb(23, 63, 53));
            Controls.Add(setupHeading);




            statusLabel.Location = new Point(32, 372);
            statusLabel.Size = new Size(696, 34);
            statusLabel.Text = startupPlanStaged ? "Community Explorer plan ready. Checking RERC-e..." : "Checking RERC-e...";
            statusLabel.ForeColor = Color.FromArgb(70, 80, 75);
            statusLabel.AccessibleName = "RERC-e status";
            statusLabel.AccessibleDescription = statusLabel.Text;
            Controls.Add(statusLabel);

            progressBar.Location = new Point(32, 414);
            progressBar.Size = new Size(696, 12);
            progressBar.Style = ProgressBarStyle.Continuous;
            progressBar.AccessibleName = "RERC-e setup progress";
            progressBar.AccessibleDescription = "Shows download and startup progress.";
            Controls.Add(progressBar);

            startButton.Text = "&Start RERC-e";
            startButton.Location = new Point(32, 451);
            startButton.Size = new Size(190, 46);
            StylePrimary(startButton);
            startButton.Click += StartClicked;
            Controls.Add(startButton);

            openButton.Text = "&Open RERC-e";
            openButton.Location = new Point(234, 451);
            openButton.Size = new Size(140, 46);
            StyleSecondary(openButton);
            openButton.Click += async delegate { await OpenAppAsync(); };
            Controls.Add(openButton);

            stopButton.Text = "&Stop";
            stopButton.Location = new Point(386, 451);
            stopButton.Size = new Size(100, 46);
            StyleSecondary(stopButton);
            stopButton.Click += StopClicked;
            Controls.Add(stopButton);
            AcceptButton = startButton;
            CancelButton = stopButton;

            browserPanel.Dock = DockStyle.Fill;
            browserPanel.BackColor = Color.White;
            browserPanel.Visible = false;
            appView.Dock = DockStyle.Fill;
            browserPanel.Controls.Add(appView);
            setupButton.Text = "Setup and status";
            setupButton.Dock = DockStyle.Top;
            setupButton.Height = 38;
            setupButton.FlatStyle = FlatStyle.Flat;
            setupButton.BackColor = Color.FromArgb(243, 247, 244);
            setupButton.ForeColor = Color.FromArgb(23, 63, 53);
            setupButton.Click += delegate { ShowSetup(); };
            browserPanel.Controls.Add(setupButton);
            Controls.Add(browserPanel);
            browserPanel.BringToFront();

#if RERC_E_ACCEPTANCE_QA
            Shown += delegate
            {
                statusLabel.Text = "Native acceptance preview. No model download will run.";
                RefreshButtons();
            };
#else
            Shown += async delegate { await RefreshStateAsync(); };
#endif
            FormClosed += delegate { int failures; Runtime.StopOwnedProcesses(out failures); };
            // Programmatic WinForms controls do not receive the designer-generated
            // initial scale pass. Scale the complete 96-DPI layout once after it
            // exists, then retain that baseline for future per-monitor DPI changes.
            ApplyInitialDpiScale();
        }

        private void ApplyInitialDpiScale()
        {
            int dpi = Math.Max(96, DeviceDpi);
            if (dpi != 96)
            {
                SuspendLayout();
                Scale(new SizeF(dpi / 96f, dpi / 96f));
                ResumeLayout(true);
            }
            AutoScaleDimensions = new SizeF(dpi, dpi);
        }

        private int ScaleLogical(int value)
        {
            return (int)Math.Round(value * DpiAwareness.WindowDpi(this) / 96d);
        }

        private Label MakeLabel(string text, int x, int y, int width, int height, float size, bool bold, Color color)
        {
            Label label = new Label();
            label.Text = text;
            label.Location = new Point(x, y);
            label.Size = new Size(width, height);
            label.Font = new Font("Segoe UI", size, bold ? FontStyle.Bold : FontStyle.Regular);
            label.ForeColor = color;
            return label;
        }

        private LinkLabel MakeLink(string text, int x, int y, int width, string url)
        {
            LinkLabel link = new LinkLabel();
            link.Text = text;
            link.Location = new Point(x, y);
            link.Size = new Size(width, 24);
            link.LinkColor = Color.FromArgb(27, 106, 143);
            link.LinkClicked += delegate { Runtime.OpenBrowser(url); };
            return link;
        }

        private void StylePrimary(Button button)
        {
            button.BackColor = Color.FromArgb(0, 87, 63);
            button.ForeColor = Color.White;
            button.FlatStyle = FlatStyle.Flat;
            button.FlatAppearance.BorderColor = Color.FromArgb(0, 87, 63);
        }

        private void StyleSecondary(Button button)
        {
            button.BackColor = Color.White;
            button.ForeColor = Color.FromArgb(23, 63, 53);
            button.FlatStyle = FlatStyle.Flat;
            button.FlatAppearance.BorderColor = Color.FromArgb(178, 197, 184);
        }

        private async Task RefreshStateAsync()
        {
            busy = true;
            RefreshButtons();
            try
            {
                statusLabel.Text = "Checking the installed files...";
                await Task.Run((Action)Runtime.VerifyPackage);
                bool modelReady = await Task.Run((Func<bool>)Runtime.ModelReady);
                bool appReady = Runtime.AppReady();

                statusLabel.Text = appReady ? "RERC-e is ready. Open the app." : modelReady ? "The local model is ready. Start RERC-e when you are ready." : "Select Download and start. RERC-e will check the model before it runs.";
                if (startupPlanStaged) statusLabel.Text += " Your Community Explorer plan will open with it.";
                if (appReady) await OpenAppAsync();
            }
            catch (Exception error)
            {
                statusLabel.Text = error.Message;
                statusLabel.ForeColor = Color.FromArgb(139, 30, 30);
            }
            finally
            {
                busy = false;
                progressBar.Value = 0;
                RefreshButtons();
            }
        }

        private void RefreshButtons()
        {
            bool appReady = Runtime.AppReady();
            bool modelExists = File.Exists(Runtime.ModelPath) && new FileInfo(Runtime.ModelPath).Length == Config.ModelBytes;
            startButton.Text = modelExists ? "&Start RERC-e" : "&Download and start";
            // WinForms does not enlarge a fixed button when the first-run label changes.
            startButton.Width = Math.Max(ScaleLogical(190), TextRenderer.MeasureText(startButton.Text.Replace("&", ""), startButton.Font).Width + ScaleLogical(28));
            openButton.Left = startButton.Right + ScaleLogical(8);
            stopButton.Left = openButton.Right + ScaleLogical(8);
            startButton.Enabled = !busy && !appReady;
            openButton.Enabled = !busy && appReady;
            stopButton.Text = busy ? "&Cancel" : "&Stop";
            stopButton.Enabled = busy || appReady;
        }

        private async void StartClicked(object sender, EventArgs args)
        {
            busy = true;
            activeOperationCancellation = new CancellationTokenSource();
            statusLabel.ForeColor = Color.FromArgb(70, 80, 75);
            RefreshButtons();
            try
            {
                statusLabel.Text = "Checking the installed files...";
                await Task.Run((Action)Runtime.VerifyPackage);
                if (!Runtime.VcRuntimeReady()) await InstallWindowsRuntimeAsync(activeOperationCancellation.Token);
                bool modelReady = await Task.Run((Func<bool>)Runtime.ModelReady);
                if (!modelReady)
                {

                    Runtime.EnsureDownloadSpace(Runtime.ModelPath, Config.ModelBytes);
                    statusLabel.Text = "Downloading the local model...";
                    await Runtime.DownloadAsync(Config.ModelUrl, Runtime.ModelPath, UpdateDownloadProgress, activeOperationCancellation.Token);
                    statusLabel.Text = "Checking the model file...";
                    modelReady = await Task.Run((Func<bool>)Runtime.ModelReady);
                    if (!modelReady)
                    {
                        try { File.Delete(Runtime.ModelPath); } catch { }
                        throw new InvalidOperationException("The model did not pass its safety check. It was removed. Try again.");
                    }
                }
                await StartServicesAsync();
                progressBar.Value = 100;
                statusLabel.Text = startupPlanStaged ? "RERC-e is ready. Your Community Explorer plan is opening." : "RERC-e is ready. Opening the app.";
                await OpenAppAsync();
            }
            catch (Exception error)
            {
                statusLabel.Text = error.Message;
                statusLabel.ForeColor = Color.FromArgb(139, 30, 30);
                MessageBox.Show(this, error.Message, "RERC-e could not start", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            finally
            {
                busy = false;
                if (activeOperationCancellation != null) { activeOperationCancellation.Dispose(); activeOperationCancellation = null; }
                RefreshButtons();
            }
        }

        private async Task OpenAppAsync()
        {
            bool runtimeMissing = false;
            try
            {
                if (!Runtime.AppReady()) throw new InvalidOperationException("RERC-e's local service is not ready yet.");
                // Keep local service credentials inside the app's own WebView2 profile.
                string profile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "RERC-e", "WebView2");
                Directory.CreateDirectory(profile);
                if (appView.CoreWebView2 == null)
                {
                    if (appEnvironment == null) appEnvironment = await CoreWebView2Environment.CreateAsync(null, profile);
                    await appView.EnsureCoreWebView2Async(appEnvironment);
                }
                if (!viewConfigured)
                {
                    appView.CoreWebView2.Settings.AreDevToolsEnabled = false;
                    appView.CoreWebView2.Settings.IsStatusBarEnabled = false;
                    appView.CoreWebView2.NewWindowRequested += delegate(object sender, CoreWebView2NewWindowRequestedEventArgs args)
                    {
                        args.Handled = true;
                        OpenExternalPage(args.Uri);
                    };
                    appView.NavigationStarting += delegate(object sender, CoreWebView2NavigationStartingEventArgs args)
                    {
                        Uri target;
                        if (Uri.TryCreate(args.Uri, UriKind.Absolute, out target)
                            && (target.Scheme != "http" || target.Host != "127.0.0.1" || target.Port != 8789))
                        {
                            args.Cancel = true;
                            OpenExternalPage(args.Uri);
                        }
                    };
                    viewConfigured = true;
                }
                browserPanel.Visible = true;
                browserPanel.BringToFront();
                AcceptButton = null;
                CancelButton = null;
                AutoScroll = false;
                ClientSize = new Size(ScaleLogical(1180), ScaleLogical(780));
                MinimumSize = new Size(ScaleLogical(700), ScaleLogical(540));
                appView.CoreWebView2.Navigate(Runtime.AppBrowserUrl());
                appView.Focus();
            }
            catch (WebView2RuntimeNotFoundException)
            {
                runtimeMissing = true;
            }
            catch (Exception error)
            {
                statusLabel.Text = "The app window could not open: " + error.Message;
                MessageBox.Show(this, statusLabel.Text, "RERC-e app window", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            if (runtimeMissing)
            {
                if (webViewRuntimeInstallAttempted)
                {
                    statusLabel.Text = "Microsoft WebView2 is still unavailable after installation. Restart RERC-e or repair the WebView2 Runtime.";
                    MessageBox.Show(this, statusLabel.Text, "RERC-e app window", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }
                try
                {
                    await InstallWebView2RuntimeAsync();
                    webViewRuntimeInstallAttempted = true;
                    await OpenAppAsync();
                }
                catch (Exception error)
                {
                    statusLabel.Text = "The app display component could not be installed: " + error.Message;
                    MessageBox.Show(this, statusLabel.Text, "RERC-e app window", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            }
        }

#if RERC_E_ACCEPTANCE_QA
        internal WebView2 AcceptanceWebView { get { return appView; } }

        internal void PrepareAcceptanceSetup()
        {
            ShowSetup();
            statusLabel.Text = "Native acceptance preview. No model download will run.";
            RefreshButtons();
            PerformLayout();
        }

        internal async Task<string> OpenAcceptanceAppAsync(string address, string profile)
        {
            Uri allowed = new Uri(address);
            if (appEnvironment == null) appEnvironment = await CoreWebView2Environment.CreateAsync(null, profile);
            await appView.EnsureCoreWebView2Async(appEnvironment);
            if (appView.CoreWebView2 == null) throw new InvalidOperationException("The WebView2 control did not initialize.");
            appView.CoreWebView2.Settings.AreDevToolsEnabled = false;
            appView.CoreWebView2.Settings.IsStatusBarEnabled = false;
            appView.CoreWebView2.NewWindowRequested += delegate(object sender, CoreWebView2NewWindowRequestedEventArgs args)
            {
                args.Handled = true;
            };
            appView.NavigationStarting += delegate(object sender, CoreWebView2NavigationStartingEventArgs args)
            {
                Uri target;
                if (!Uri.TryCreate(args.Uri, UriKind.Absolute, out target)
                    || target.Scheme != allowed.Scheme
                    || !string.Equals(target.Host, allowed.Host, StringComparison.OrdinalIgnoreCase)
                    || target.Port != allowed.Port)
                    args.Cancel = true;
            };
            browserPanel.Visible = true;
            browserPanel.BringToFront();
            AcceptButton = null;
            CancelButton = null;
            AutoScroll = false;
            ClientSize = new Size(ScaleLogical(1180), ScaleLogical(780));
            MinimumSize = new Size(ScaleLogical(700), ScaleLogical(540));

            TaskCompletionSource<bool> navigation = new TaskCompletionSource<bool>();
            EventHandler<CoreWebView2NavigationCompletedEventArgs> completed = null;
            completed = delegate(object sender, CoreWebView2NavigationCompletedEventArgs args)
            {
                Uri completedUri;
                if (!Uri.TryCreate(appView.CoreWebView2.Source, UriKind.Absolute, out completedUri)
                    || completedUri.Scheme != allowed.Scheme
                    || !string.Equals(completedUri.Host, allowed.Host, StringComparison.OrdinalIgnoreCase)
                    || completedUri.Port != allowed.Port)
                    return;
                appView.CoreWebView2.NavigationCompleted -= completed;
                if (args.IsSuccess) navigation.TrySetResult(true);
                else navigation.TrySetException(new InvalidOperationException("The embedded RERC-e page did not finish navigation."));
            };
            appView.CoreWebView2.NavigationCompleted += completed;
            appView.CoreWebView2.Navigate(address);
            await navigation.Task;
            appView.Focus();
            return await appView.CoreWebView2.ExecuteScriptAsync("JSON.stringify({title:document.title,projectVisible:!document.getElementById('projectStep').hidden,stepCount:document.querySelectorAll('.journey button').length,tokenStored:!!sessionStorage.getItem('rercie.tabSessionToken.v1'),pageOverflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1})");
        }
#endif

        private async Task InstallWebView2RuntimeAsync()
        {
            DialogResult choice = MessageBox.Show(this,
                "RERC-e needs Microsoft's WebView2 Runtime to display the app in this window. Download and install the official Microsoft component now?",
                "Install app display component", MessageBoxButtons.OKCancel, MessageBoxIcon.Information);
            if (choice != DialogResult.OK) throw new InvalidOperationException("The app display component was not installed.");
            string installer = Path.Combine(Path.GetTempPath(), "RERC-e-WebView2Setup.exe");
            statusLabel.Text = "Downloading the Microsoft app display component...";
            await Runtime.DownloadAsync("https://go.microsoft.com/fwlink/p/?LinkId=2124703", installer, null, CancellationToken.None);
            if (!AuthenticodeVerifier.IsTrustedMicrosoftFile(installer))
            {
                try { File.Delete(installer); } catch { }
                throw new InvalidOperationException("The Microsoft component did not pass its publisher signature check.");
            }
            statusLabel.Text = "Installing the Microsoft app display component...";
            ProcessStartInfo info = new ProcessStartInfo(installer, "/silent /install");
            info.UseShellExecute = true;
            Process process = Process.Start(info);
            if (process == null) throw new InvalidOperationException("The Microsoft component could not start.");
            await Task.Run((Action)(() => process.WaitForExit()));
            try { File.Delete(installer); } catch { }
            if (process.ExitCode != 0) throw new InvalidOperationException("The Microsoft component returned error " + process.ExitCode + ".");
            CoreWebView2Environment.GetAvailableBrowserVersionString();
        }

        private static void OpenExternalPage(string address)
        {
            Uri target;
            if (Uri.TryCreate(address, UriKind.Absolute, out target) && (target.Scheme == "https" || target.Scheme == "http"))
                Runtime.OpenBrowser(target.AbsoluteUri);
        }

        private void ShowSetup()
        {
            browserPanel.Visible = false;
            AcceptButton = startButton;
            CancelButton = stopButton;
            AutoScroll = true;
            ClientSize = new Size(ScaleLogical(760), ScaleLogical(540));
            MinimumSize = new Size(ScaleLogical(776), ScaleLogical(579));
            RefreshButtons();
        }

        protected override void WndProc(ref Message message)
        {
            if (message.Msg == Program.OpenAppMessage)
            {
                BeginInvoke(new Action(async delegate { await OpenAppAsync(); }));
                return;
            }
            base.WndProc(ref message);
        }

        private void UpdateDownloadProgress(long done, long total)
        {
            long expected = total > 0 ? total : Config.ModelBytes;
            int percent = (int)Math.Max(0, Math.Min(100, done * 100L / Math.Max(1L, expected)));
            progressBar.Value = percent;
            statusLabel.Text = string.Format("Downloading the local model... {0}% ({1:0.0} of {2:0.0} MB)", percent, done / 1048576d, expected / 1048576d);
        }

        private async Task InstallWindowsRuntimeAsync(CancellationToken cancellationToken)
        {
            DialogResult choice = MessageBox.Show(this, "RERC-e needs a standard Microsoft Windows component. Windows may ask for permission while the official Microsoft installer runs.", "One Windows component is needed", MessageBoxButtons.OKCancel, MessageBoxIcon.Information);
            if (choice != DialogResult.OK) throw new InvalidOperationException("Setup stopped before the Windows component was installed.");
            string installer = Path.Combine(Path.GetTempPath(), "RERC-e-vc_redist.x64.exe");
            statusLabel.Text = "Downloading the Microsoft Windows component...";
            await Runtime.DownloadAsync(Config.VcRuntimeUrl, installer, null, cancellationToken);
            if (!AuthenticodeVerifier.IsTrustedMicrosoftFile(installer))
            {
                try { File.Delete(installer); } catch { }
                throw new InvalidOperationException("The Microsoft installer did not pass its signature check.");
            }
            ProcessStartInfo info = new ProcessStartInfo(installer, "/install /quiet /norestart");
            info.UseShellExecute = true;
            info.Verb = "runas";
            Process process = Process.Start(info);
            if (process == null) throw new InvalidOperationException("The Microsoft installer could not start.");
            process.WaitForExit();
            try { File.Delete(installer); } catch { }
            if (process.ExitCode != 0 && process.ExitCode != 1638 && process.ExitCode != 3010) throw new InvalidOperationException("The Microsoft installer returned error " + process.ExitCode + ".");
            if (!Runtime.VcRuntimeReady()) throw new InvalidOperationException("The Windows component is still missing. Restart Windows, then open RERC-e again.");
        }

        private async Task StartServicesAsync()
        {
            if (!Runtime.ModelServerReady())
            {
                if (Runtime.PortInUse(8788)) throw new InvalidOperationException("Another program is blocking RERC-e. Close it, then start RERC-e again.");
                int threads = Math.Max(2, Environment.ProcessorCount - 1);
                string llamaArgs = "-m \"" + Runtime.ModelPath + "\" --host 127.0.0.1 --port 8788 -c 8192 -t " + threads;
                Runtime.StartHidden("llama", Runtime.LlamaExe, llamaArgs, Runtime.LlamaDir, null, null);
                statusLabel.Text = "Starting the local writing model...";
                await Runtime.WaitForAsync(Runtime.ModelServerReady, 150, "The local model did not start. Restart RERC-e and try again.");
            }
            if (!Runtime.AppReady())
            {
                if (Runtime.PortInUse(8789)) throw new InvalidOperationException("Another program is blocking RERC-e. Close it, then start RERC-e again.");
                string sessionToken = Runtime.CreateSessionToken();
                Dictionary<string, string> environment = new Dictionary<string, string>();
                environment["RERCIE_LOCAL_CHAT_URL"] = "http://127.0.0.1:8788/v1/chat/completions";
                environment["RERCIE_LOCAL_HEALTH_URL"] = Config.ModelHealthUrl;
                environment["RERCIE_LOCAL_MODELS_URL"] = Config.ModelListUrl;
                environment["RERCIE_SESSION_TOKEN"] = sessionToken;
                environment["RERCIE_EXPECTED_HOST"] = "127.0.0.1:8789";
                environment["RERCIE_APP_ROOT"] = Runtime.Root;
                Runtime.StartHidden("app", Runtime.ServiceExe, "--serve --host 127.0.0.1 --port 8789", Runtime.ServiceDir, environment, sessionToken);
                statusLabel.Text = "Starting RERC-e...";
                await Runtime.WaitForAsync(Runtime.AppReady, 35, "RERC-e did not start. Restart the app and try again.");
            }
        }

        private async void StopClicked(object sender, EventArgs args)
        {
            if (busy && activeOperationCancellation != null)
            {
                activeOperationCancellation.Cancel();
                statusLabel.Text = "Canceling the current operation...";
                return;
            }
            busy = true;
            statusLabel.ForeColor = Color.FromArgb(70, 80, 75);
            RefreshButtons();
            try
            {
                int failures = 0;
                int stopped = await Task.Run(() => Runtime.StopOwnedProcesses(out failures));
                statusLabel.Text = failures > 0 ? "RERC-e could not stop every local process. Close RERC-e and try again." : stopped > 0 ? "RERC-e stopped." : "RERC-e was already stopped.";
                if (failures > 0) statusLabel.ForeColor = Color.FromArgb(139, 30, 30);
            }
            catch (Exception error)
            {
                statusLabel.Text = "RERC-e could not stop: " + error.Message;
                statusLabel.ForeColor = Color.FromArgb(139, 30, 30);
            }
            finally
            {
                progressBar.Value = 0;
                busy = false;
                RefreshButtons();
            }
        }
    }

    internal static class AuthenticodeVerifier
    {
        private static readonly Guid VerifyAction = new Guid("00AAC56B-CD44-11d0-8CC2-00C04FC295EE");

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct WinTrustFileInfo
        {
            public uint cbStruct;
            [MarshalAs(UnmanagedType.LPWStr)] public string pcwszFilePath;
            public IntPtr hFile;
            public IntPtr pgKnownSubject;
        }

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct WinTrustData
        {
            public uint cbStruct;
            public IntPtr pPolicyCallbackData;
            public IntPtr pSIPClientData;
            public uint dwUIChoice;
            public uint fdwRevocationChecks;
            public uint dwUnionChoice;
            public IntPtr pFile;
            public uint dwStateAction;
            public IntPtr hWVTStateData;
            public IntPtr pwszURLReference;
            public uint dwProvFlags;
            public uint dwUIContext;
        }

        [DllImport("wintrust.dll", ExactSpelling = true, SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern uint WinVerifyTrust(IntPtr hwnd, [MarshalAs(UnmanagedType.LPStruct)] Guid action, IntPtr data);

        public static bool IsTrustedMicrosoftFile(string path)
        {
            IntPtr filePtr = IntPtr.Zero;
            IntPtr dataPtr = IntPtr.Zero;
            try
            {
                WinTrustFileInfo file = new WinTrustFileInfo();
                file.cbStruct = (uint)Marshal.SizeOf(typeof(WinTrustFileInfo));
                file.pcwszFilePath = path;
                filePtr = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(WinTrustFileInfo)));
                Marshal.StructureToPtr(file, filePtr, false);

                WinTrustData data = new WinTrustData();
                data.cbStruct = (uint)Marshal.SizeOf(typeof(WinTrustData));
                data.dwUIChoice = 2;
                data.fdwRevocationChecks = 0;
                data.dwUnionChoice = 1;
                data.pFile = filePtr;
                data.dwStateAction = 0;
                data.dwProvFlags = 0;
                dataPtr = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(WinTrustData)));
                Marshal.StructureToPtr(data, dataPtr, false);
                if (WinVerifyTrust(IntPtr.Zero, VerifyAction, dataPtr) != 0) return false;
                X509Certificate2 certificate = new X509Certificate2(X509Certificate.CreateFromSignedFile(path));
                return certificate.Subject.IndexOf("Microsoft Corporation", StringComparison.OrdinalIgnoreCase) >= 0;
            }
            catch { return false; }
            finally
            {
                if (dataPtr != IntPtr.Zero) { Marshal.DestroyStructure(dataPtr, typeof(WinTrustData)); Marshal.FreeHGlobal(dataPtr); }
                if (filePtr != IntPtr.Zero) { Marshal.DestroyStructure(filePtr, typeof(WinTrustFileInfo)); Marshal.FreeHGlobal(filePtr); }
            }
        }
    }

    internal static class Program
    {
        internal const int OpenAppMessage = 0x8001;
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern IntPtr FindWindow(string className, string windowName);
        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr window, int command);
        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr window);
        [DllImport("user32.dll")]
        private static extern bool PostMessage(IntPtr window, int message, IntPtr wParam, IntPtr lParam);

        private static bool ActivateExistingWindow()
        {
            IntPtr window = FindWindow(null, "RERC-e");
            if (window == IntPtr.Zero) return false;
            ShowWindow(window, 9);
            SetForegroundWindow(window);
            PostMessage(window, OpenAppMessage, IntPtr.Zero, IntPtr.Zero);
            return true;
        }
        [STAThread]
        private static int Main(string[] args)
        {
            DpiAwareness.Initialize();
            if (Array.IndexOf(args, "--stop") >= 0)
            {
                int failures;
                Runtime.StopOwnedProcesses(out failures);
                return failures == 0 ? 0 : 1;
            }
            int probeIndex = Array.IndexOf(args, "--probe-download-output");
            if (probeIndex >= 0 && probeIndex + 1 < args.Length)
            {
                try
                {
                    object result = Runtime.ProbeModelDownloadAsync().GetAwaiter().GetResult();
                    File.WriteAllText(args[probeIndex + 1], new JavaScriptSerializer().Serialize(result), new UTF8Encoding(false));
                    return 0;
                }
                catch (Exception error)
                {
                    File.WriteAllText(args[probeIndex + 1], "{\"status\":\"FAIL\",\"error\":" + new JavaScriptSerializer().Serialize(error.Message) + "}", new UTF8Encoding(false));
                    return 1;
                }
            }
            int smokeIndex = Array.IndexOf(args, "--smoke-output");
            if (smokeIndex >= 0 && smokeIndex + 1 < args.Length)
            {
                try
                {
                    Runtime.VerifyPackage();
                    string json = new JavaScriptSerializer().Serialize(new
                    {
                        status = "PASS",
                        app = "RERC-e",
                        version = Config.Version,
                        powershell_required = false,
                        model_name = Config.ModelName,
                        model_sha256 = Config.ModelSha256,
                        model_source = Config.ModelPageUrl,
                        model_download_bytes = Config.ModelBytes,
                        plan_schema = Config.PlanSchema,
                        plan_version = Config.PlanVersion,
                        plan_max_bytes = Config.MaxPlanBytes,
                        plan_extensions = new[] { ".rerc-e", ".rercie", ".json" },
                        launcher = Application.ExecutablePath
                    });
                    File.WriteAllText(args[smokeIndex + 1], json, new UTF8Encoding(false));
                    return 0;
                }
                catch (Exception error)
                {
                    File.WriteAllText(args[smokeIndex + 1], "{\"status\":\"FAIL\",\"error\":" + new JavaScriptSerializer().Serialize(error.Message) + "}", new UTF8Encoding(false));
                    return 1;
                }
            }

            string planPath = null;
            foreach (string argument in args)
            {
                if (argument.StartsWith("--", StringComparison.Ordinal)) continue;
                string extension = Path.GetExtension(argument);
                if (string.Equals(extension, ".rerc-e", StringComparison.OrdinalIgnoreCase)
                    || string.Equals(extension, ".rercie", StringComparison.OrdinalIgnoreCase)
                    || string.Equals(extension, ".json", StringComparison.OrdinalIgnoreCase))
                {
                    planPath = argument;
                    break;
                }
            }
            bool planStaged = false;
            if (!string.IsNullOrWhiteSpace(planPath))
            {
                try
                {
                    Runtime.StagePlanFile(planPath);
                    planStaged = true;
                }
                catch (Exception error)
                {
                    MessageBox.Show(error.Message, "RERC-e could not open this plan", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return 2;
                }
            }

            bool created;
            using (Mutex mutex = new Mutex(true, "Local\\RERC-e-Desktop", out created))
            {
                if (!created)
                {
                    if (!Runtime.AppReady())
                    {
                        if (planStaged)
                        {
                            MessageBox.Show("The plan is ready. Use the open RERC-e window to start the app.", "Community Explorer plan ready", MessageBoxButtons.OK, MessageBoxIcon.Information);
                            return 0;
                        }
                        return 1;
                    }
                    return ActivateExistingWindow() ? 0 : 1;
                }
                if (planStaged && Runtime.AppReady())
                {
                    Application.EnableVisualStyles();
                    Application.SetCompatibleTextRenderingDefault(false);
                    Application.Run(new MainForm(true));
                    return 0;
                }
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                Application.Run(new MainForm(planStaged));
            }
            return 0;
        }
    }
}
