using System.Diagnostics;

namespace DokaponSoFTools.Core.Tools;

public sealed record VideoInfo(
    string Path, int Width = 0, int Height = 0,
    double Duration = 0, double Fps = 0,
    string Codec = "", string AudioCodec = "", long FileSize = 0
)
{
    public string Resolution => $"{Width}x{Height}";
    public string DurationStr => $"{(int)(Duration / 60):D2}:{(int)(Duration % 60):D2}";
    public string FileSizeStr => FileSize switch
    {
        < 1024 => $"{FileSize} B",
        < 1024 * 1024 => $"{FileSize / 1024.0:F1} KB",
        _ => $"{FileSize / (1024.0 * 1024):F1} MB"
    };
}

public sealed class ConversionSettings
{
    public int Width { get; set; } = 1280;
    public int Height { get; set; } = 720;
    public double Fps { get; set; } = 29.97;
    public int VideoQuality { get; set; } = 8;
    public int AudioQuality { get; set; } = 4;
    public int AudioSampleRate { get; set; } = 48000;
    public bool MaintainAspect { get; set; } = true;
}

public sealed class VideoConverter
{
    private readonly string _ffmpegPath;
    private readonly string _ffprobePath;

    public VideoConverter(string? ffmpegPath = null, string? ffprobePath = null)
    {
        var tm = ToolManager.Instance;
        _ffmpegPath = ffmpegPath ?? tm.FfmpegPath;
        _ffprobePath = ffprobePath ?? tm.FfprobePath;
    }

    public async Task<VideoInfo> GetVideoInfoAsync(string path)
    {
        if (!File.Exists(path))
            return new VideoInfo(path);

        long fileSize = new FileInfo(path).Length;
        int width = 0, height = 0;
        double duration = 0, fps = 0;
        string codec = "", audioCodec = "";

        try
        {
            string output = await RunProcessAsync(_ffprobePath,
                $"-v quiet -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name,duration -of csv=p=0 \"{path}\"");

            if (!string.IsNullOrWhiteSpace(output))
            {
                var parts = output.Trim().Split(',');
                if (parts.Length >= 4)
                {
                    int.TryParse(parts[0], out width);
                    int.TryParse(parts[1], out height);
                    if (parts[2].Contains('/'))
                    {
                        var frac = parts[2].Split('/');
                        if (double.TryParse(frac[0], out double num) && double.TryParse(frac[1], out double den) && den > 0)
                            fps = num / den;
                    }
                    else double.TryParse(parts[2], out fps);
                    codec = parts[3];
                    if (parts.Length > 4) double.TryParse(parts[4], out duration);
                }
            }

            string audioOutput = await RunProcessAsync(_ffprobePath,
                $"-v quiet -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 \"{path}\"");
            audioCodec = audioOutput.Trim();
        }
        catch { /* ignore probe errors */ }

        return new VideoInfo(path, width, height, duration, fps, codec, audioCodec, fileSize);
    }

    public async Task<bool> ConvertToGameFormatAsync(string inputPath, string outputPath,
        ConversionSettings? settings = null, IProgress<double>? progress = null)
    {
        settings ??= new ConversionSettings();
        if (!File.Exists(inputPath)) return false;

        string tempDir = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"dokapon_video_{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDir);
        string tempMp4 = System.IO.Path.Combine(tempDir, "temp.mp4");

        try
        {
            progress?.Report(0.1);

            // Step 1: to MP4
            string vf = settings.MaintainAspect
                ? $"scale={settings.Width}:{settings.Height}:force_original_aspect_ratio=decrease,pad={settings.Width}:{settings.Height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
                : $"scale={settings.Width}:{settings.Height},setsar=1";

            bool ok = await RunFfmpegAsync(
                $"-y -i \"{inputPath}\" -vf \"{vf}\" -r {settings.Fps} -ar {settings.AudioSampleRate} -pix_fmt yuv420p -movflags +faststart \"{tempMp4}\"");
            if (!ok) return false;

            progress?.Report(0.5);

            // Step 2: MP4 to OGV
            Directory.CreateDirectory(System.IO.Path.GetDirectoryName(outputPath) ?? ".");
            ok = await RunFfmpegAsync(
                $"-y -i \"{tempMp4}\" -c:v libtheora -q:v {settings.VideoQuality} -c:a libvorbis -q:a {settings.AudioQuality} -ac 2 \"{outputPath}\"");
            if (!ok) return false;

            progress?.Report(1.0);
            return File.Exists(outputPath) && new FileInfo(outputPath).Length > 0;
        }
        finally
        {
            try
            {
                if (File.Exists(tempMp4)) File.Delete(tempMp4);
                if (Directory.Exists(tempDir)) Directory.Delete(tempDir, true);
            }
            catch { /* cleanup best-effort */ }
        }
    }

    private async Task<bool> RunFfmpegAsync(string arguments)
    {
        var psi = new ProcessStartInfo(_ffmpegPath, arguments)
        {
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false
        };
        using var proc = Process.Start(psi);
        if (proc is null) return false;
        await proc.WaitForExitAsync();
        return proc.ExitCode == 0;
    }

    private static async Task<string> RunProcessAsync(string exe, string arguments)
    {
        var psi = new ProcessStartInfo(exe, arguments)
        {
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            UseShellExecute = false
        };
        using var proc = Process.Start(psi)!;
        string output = await proc.StandardOutput.ReadToEndAsync();
        await proc.WaitForExitAsync();
        return output;
    }

    public static List<string> FindGameVideos(string gameDir)
    {
        var ogvFiles = new HashSet<string>();
        string[] searchPaths = [
            gameDir,
            System.IO.Path.Combine(gameDir, "GameData", "app"),
            System.IO.Path.Combine(gameDir, "data"),
            System.IO.Path.Combine(gameDir, "movies")
        ];

        foreach (string searchPath in searchPaths)
        {
            if (!Directory.Exists(searchPath)) continue;
            foreach (string file in Directory.EnumerateFiles(searchPath, "*.ogv", SearchOption.AllDirectories))
                ogvFiles.Add(file);
        }

        return ogvFiles.OrderBy(f => f).ToList();
    }
}
