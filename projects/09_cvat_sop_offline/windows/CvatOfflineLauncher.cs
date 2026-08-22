using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

[assembly: AssemblyTitle("CVAT中文离线标注平台")]
[assembly: AssemblyDescription("CVAT 2.73.1 中文固定版 Docker 离线启动器")]
[assembly: AssemblyProduct("CVAT中文离线标注平台")]
[assembly: AssemblyVersion("2.73.1.0")]
[assembly: AssemblyFileVersion("2.73.1.0")]

namespace CvatOfflineLauncher
{
    internal static class Program
    {
        private static Mutex singleInstance;

        [STAThread]
        private static void Main()
        {
            bool created;
            singleInstance = new Mutex(true, "CVAT.zhCN.offline.2.73.1", out created);
            if (!created)
            {
                MessageBox.Show("启动器已在运行。", "CVAT中文离线版", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
            singleInstance.ReleaseMutex();
        }
    }

    internal sealed class MainForm : Form
    {
        private const string SiteUrl = "http://127.0.0.1:8081";
        private readonly string appRoot;
        private readonly string logPath;
        private readonly Label stateLabel;
        private readonly Label detailLabel;
        private readonly Button startButton;
        private readonly Button stopButton;
        private readonly Button openButton;
        private readonly ProgressBar progress;
        private readonly System.Windows.Forms.Timer healthTimer;
        private bool busy;

        internal MainForm()
        {
            appRoot = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            Directory.CreateDirectory(Path.Combine(appRoot, "logs"));
            logPath = Path.Combine(appRoot, "logs", "cvat-launcher.log");

            Text = "CVAT中文离线标注平台";
            Size = new Size(690, 405);
            MinimumSize = new Size(690, 405);
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(244, 246, 247);
            Font = new Font("Microsoft YaHei UI", 9F);

            Controls.Add(new Label {
                Text = "CVAT中文离线标注平台",
                Font = new Font("Microsoft YaHei UI", 19F, FontStyle.Bold),
                AutoSize = true,
                Location = new Point(38, 28),
                ForeColor = Color.FromArgb(23, 43, 58)
            });
            Controls.Add(new Label {
                Text = "CVAT 2.73.1  ·  固定中文界面  ·  矩形框十字准星  ·  本机数据卷",
                AutoSize = true,
                Location = new Point(41, 72),
                ForeColor = Color.FromArgb(83, 102, 112)
            });

            Panel statusPanel = new Panel {
                Location = new Point(42, 106), Size = new Size(590, 112),
                BackColor = Color.White, BorderStyle = BorderStyle.FixedSingle
            };
            stateLabel = new Label {
                Text = "正在检查服务",
                Font = new Font("Microsoft YaHei UI", 13F, FontStyle.Bold),
                AutoSize = true, Location = new Point(20, 17),
                ForeColor = Color.FromArgb(38, 132, 105)
            };
            detailLabel = new Label {
                Text = SiteUrl, AutoEllipsis = true,
                Location = new Point(21, 52), Size = new Size(545, 32),
                ForeColor = Color.FromArgb(91, 108, 119)
            };
            progress = new ProgressBar {
                Location = new Point(22, 87), Size = new Size(544, 8),
                Style = ProgressBarStyle.Marquee, Visible = false
            };
            statusPanel.Controls.AddRange(new Control[] { stateLabel, detailLabel, progress });
            Controls.Add(statusPanel);

            startButton = MakeButton("启动平台", 42, true);
            openButton = MakeButton("打开网页", 192, true);
            stopButton = MakeButton("停止服务", 342, false);
            Button folderButton = MakeButton("打开数据目录", 492, false);
            startButton.Click += async delegate { await StartPlatform(); };
            openButton.Click += delegate { OpenSite(); };
            stopButton.Click += async delegate { await StopPlatform(); };
            folderButton.Click += delegate { Process.Start("explorer.exe", appRoot); };
            Controls.AddRange(new Control[] { startButton, openButton, stopButton, folderButton });

            Controls.Add(new Label {
                Text = "首次启动会加载离线镜像，可能需要数分钟。需要 Docker Desktop + WSL2，标注数据保存在本机 Docker 卷中。",
                Location = new Point(43, 303), Size = new Size(585, 45),
                ForeColor = Color.FromArgb(126, 88, 34)
            });

            healthTimer = new System.Windows.Forms.Timer { Interval = 3000 };
            healthTimer.Tick += async delegate { await RefreshHealth(); };
            Shown += async delegate { healthTimer.Start(); await RefreshHealth(); };
        }

        private Button MakeButton(string text, int x, bool primary)
        {
            return new Button {
                Text = text, Location = new Point(x, 243), Size = new Size(130, 42),
                FlatStyle = FlatStyle.Flat,
                BackColor = primary ? Color.FromArgb(38, 132, 105) : Color.White,
                ForeColor = primary ? Color.White : Color.FromArgb(31, 62, 78)
            };
        }

        private string ComposeArguments(string action)
        {
            string main = Path.Combine(appRoot, "docker-compose.yml");
            string windows = Path.Combine(appRoot, "docker-compose.windows.yml");
            return "compose -f \"" + main + "\" -f \"" + windows + "\" " + action;
        }

        private async Task StartPlatform()
        {
            if (busy) return;
            if (!File.Exists(Path.Combine(appRoot, "docker-compose.yml")) ||
                !File.Exists(Path.Combine(appRoot, "docker-compose.windows.yml")))
            {
                MessageBox.Show("交付目录缺少 Compose 配置。", "启动失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            SetBusy(true, "正在检查 Docker Desktop");
            string dockerCheck = await RunCommand("docker", "version --format \"{{.Server.Version}}\"");
            if (!dockerCheck.StartsWith("OK\n"))
            {
                string desktop = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Docker", "Docker", "Docker Desktop.exe");
                if (File.Exists(desktop))
                {
                    Process.Start(desktop);
                    for (int i = 0; i < 60; i++)
                    {
                        await Task.Delay(3000);
                        dockerCheck = await RunCommand("docker", "version --format \"{{.Server.Version}}\"");
                        if (dockerCheck.StartsWith("OK\n")) break;
                    }
                }
            }
            if (!dockerCheck.StartsWith("OK\n"))
            {
                SetBusy(false, "Docker Desktop 未安装或未启动");
                MessageBox.Show("请先安装并启动 Docker Desktop，确保 WSL2 Linux 容器模式可用。", "Docker 不可用", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            string imageArchive = Path.Combine(appRoot, "images", "cvat-offline-amd64.tar");
            string marker = Path.Combine(appRoot, "images", ".loaded-2.73.1");
            if (!File.Exists(marker))
            {
                if (!File.Exists(imageArchive))
                {
                    SetBusy(false, "缺少离线镜像包");
                    MessageBox.Show("缺少 images\\cvat-offline-amd64.tar。", "启动失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }
                SetBusy(true, "首次启动：正在加载离线 Docker 镜像");
                string loaded = await RunCommand("docker", "load -i \"" + imageArchive + "\"");
                if (!loaded.StartsWith("OK\n"))
                {
                    SetBusy(false, "离线镜像加载失败");
                    ShowLogError(loaded);
                    return;
                }
                File.WriteAllText(marker, DateTime.Now.ToString("s"));
            }

            SetBusy(true, "正在启动 CVAT 服务");
            string started = await RunCommand("docker", ComposeArguments("up -d"));
            if (!started.StartsWith("OK\n"))
            {
                SetBusy(false, "CVAT 启动失败");
                ShowLogError(started);
                return;
            }

            for (int i = 0; i < 90; i++)
            {
                if (IsHealthy())
                {
                    SetBusy(false, "服务已就绪：" + SiteUrl);
                    OpenSite();
                    return;
                }
                detailLabel.Text = "正在等待后端健康检查（" + (i * 2) + " 秒）";
                await Task.Delay(2000);
            }
            SetBusy(false, "服务启动超时，请查看 logs\\cvat-launcher.log");
        }

        private async Task StopPlatform()
        {
            if (busy) return;
            SetBusy(true, "正在停止 CVAT（数据卷保留）");
            string stopped = await RunCommand("docker", ComposeArguments("down"));
            SetBusy(false, stopped.StartsWith("OK\n") ? "服务已停止，数据已保留" : "停止失败，请查看日志");
        }

        private async Task<string> RunCommand(string fileName, string arguments)
        {
            return await Task.Run(() => {
                try
                {
                    ProcessStartInfo info = new ProcessStartInfo {
                        FileName = "cmd.exe",
                        Arguments = "/d /s /c \"" + fileName + " " + arguments + " 2>&1\"",
                        WorkingDirectory = appRoot,
                        UseShellExecute = false,
                        CreateNoWindow = true,
                        RedirectStandardOutput = true
                    };
                    using (Process process = Process.Start(info))
                    {
                        string output = process.StandardOutput.ReadToEnd();
                        process.WaitForExit();
                        AppendLog(fileName + " " + arguments, output, process.ExitCode);
                        return (process.ExitCode == 0 ? "OK\n" : "ERROR\n") + output;
                    }
                }
                catch (Exception exception)
                {
                    AppendLog(fileName + " " + arguments, exception.ToString(), -1);
                    return "ERROR\n" + exception.Message;
                }
            });
        }

        private void AppendLog(string command, string output, int exitCode)
        {
            File.AppendAllText(logPath, DateTime.Now.ToString("s") + "  " + command + "  exit=" + exitCode + Environment.NewLine + output + Environment.NewLine);
        }

        private void ShowLogError(string output)
        {
            string message = output.Length > 1000 ? output.Substring(output.Length - 1000) : output;
            MessageBox.Show(message + "\r\n\r\n完整日志：" + logPath, "CVAT操作失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }

        private async Task RefreshHealth()
        {
            if (busy) return;
            bool online = await Task.Run(() => IsHealthy());
            stateLabel.Text = online ? "CVAT 服务在线" : "CVAT 服务未启动";
            stateLabel.ForeColor = online ? Color.FromArgb(38, 132, 105) : Color.FromArgb(185, 76, 66);
            detailLabel.Text = online ? SiteUrl : "点击“启动平台”检查 Docker 并启动固定版服务";
            startButton.Enabled = !online;
            stopButton.Enabled = online;
            openButton.Enabled = online;
        }

        private bool IsHealthy()
        {
            try
            {
                HttpWebRequest request = (HttpWebRequest)WebRequest.Create(SiteUrl + "/api/server/about");
                request.Timeout = 1200;
                using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
                    return response.StatusCode == HttpStatusCode.OK;
            }
            catch { return false; }
        }

        private void SetBusy(bool value, string detail)
        {
            busy = value;
            progress.Visible = value;
            stateLabel.Text = value ? "正在处理" : detail;
            stateLabel.ForeColor = value ? Color.FromArgb(40, 101, 145) : Color.FromArgb(38, 132, 105);
            detailLabel.Text = detail;
            startButton.Enabled = !value;
            stopButton.Enabled = !value;
            openButton.Enabled = !value && IsHealthy();
        }

        private void OpenSite()
        {
            Process.Start(new ProcessStartInfo(SiteUrl) { UseShellExecute = true });
        }
    }
}
