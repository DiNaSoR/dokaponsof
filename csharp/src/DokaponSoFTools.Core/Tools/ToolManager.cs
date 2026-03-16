using System.Diagnostics;

namespace DokaponSoFTools.Core.Tools;

public sealed class ToolManager
{
    private static ToolManager? _instance;
    private readonly Dictionary<string, string> _toolPaths = new();

    private static readonly Dictionary<string, (string Subfolder, string ExeName)> Tools = new()
    {
        ["ffmpeg"] = ("ffmpeg", "ffmpeg.exe"),
        ["ffprobe"] = ("ffmpeg", "ffprobe.exe"),
        ["opusenc"] = ("opusenc", "opusenc.exe")
    };

    public static ToolManager Instance => _instance ??= new ToolManager();

    private ToolManager()
    {
        DiscoverTools();
    }

    private void DiscoverTools()
    {
        string baseDir = AppContext.BaseDirectory;
        string toolsDir = Path.Combine(baseDir, "tools");

        foreach (var (name, (subfolder, exeName)) in Tools)
        {
            string bundled = Path.Combine(toolsDir, subfolder, exeName);
            if (File.Exists(bundled))
            {
                _toolPaths[name] = bundled;
            }
            else
            {
                string? systemPath = FindInPath(exeName);
                _toolPaths[name] = systemPath ?? exeName;
            }
        }
    }

    private static string? FindInPath(string exeName)
    {
        try
        {
            var psi = new ProcessStartInfo("where", exeName)
            {
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                UseShellExecute = false
            };
            using var proc = Process.Start(psi);
            if (proc is null) return null;
            string output = proc.StandardOutput.ReadToEnd();
            proc.WaitForExit(5000);
            return proc.ExitCode == 0 ? output.Trim().Split('\n')[0].Trim() : null;
        }
        catch { return null; }
    }

    public string GetPath(string toolName) => _toolPaths.GetValueOrDefault(toolName, toolName);
    public string FfmpegPath => GetPath("ffmpeg");
    public string FfprobePath => GetPath("ffprobe");
    public string OpusencPath => GetPath("opusenc");

    public (bool Available, string Message) VerifyTool(string toolName)
    {
        string path = GetPath(toolName);
        try
        {
            var psi = new ProcessStartInfo(path, "-version")
            {
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                UseShellExecute = false
            };
            using var proc = Process.Start(psi);
            if (proc is null) return (false, $"Tool '{toolName}' could not start");
            string output = proc.StandardOutput.ReadToEnd();
            proc.WaitForExit(10000);
            return proc.ExitCode == 0
                ? (true, output.Split('\n')[0].Trim())
                : (false, $"Tool '{toolName}' found but not responding");
        }
        catch (Exception ex)
        {
            return (false, $"Tool '{toolName}' not found: {ex.Message}");
        }
    }

    public bool IsFfmpegAvailable => VerifyTool("ffmpeg").Available;
    public bool IsOpusencAvailable => VerifyTool("opusenc").Available;
}
