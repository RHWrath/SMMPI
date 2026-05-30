using System.Runtime.InteropServices;

namespace SMMPI.Infrastructure.Adb;

/// <summary>
/// Resolves the FFmpeg executable (same discovery pattern as <see cref="AdbLocator"/>).
/// </summary>
public static class FfmpegLocator
{
    private static readonly string FfmpegFileName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "ffmpeg.exe" : "ffmpeg";
    private static readonly string FfprobeFileName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "ffprobe.exe" : "ffprobe";

    public static string Resolve()
    {
        var explicitPath = Environment.GetEnvironmentVariable("SMMPI_FFMPEG");
        if (!string.IsNullOrWhiteSpace(explicitPath) && File.Exists(explicitPath.Trim()))
        {
            return Path.GetFullPath(explicitPath.Trim());
        }

        if (TryPathDirectories(out var path))
        {
            return path;
        }

        if (TryBundledPrototypeTools(out path))
        {
            return path;
        }

        throw new FileNotFoundException(
            "FFmpeg was not found. Install FFmpeg, add it to your user PATH, " +
            "or set environment variable SMMPI_FFMPEG to the full path of ffmpeg.exe. " +
            "FFmpeg is required for the H.264 device preview (screenrecord → MJPEG).",
            FfmpegFileName);
    }

    /// <summary>
    /// Resolves ffprobe next to the resolved FFmpeg binary (bundled or on PATH).
    /// </summary>
    public static string ResolveFfprobe()
    {
        var ffmpegPath = Resolve();
        var directory = Path.GetDirectoryName(ffmpegPath);
        if (string.IsNullOrEmpty(directory))
        {
            throw new FileNotFoundException("Could not determine the directory containing FFmpeg.", FfprobeFileName);
        }

        var bundled = Path.Combine(directory, FfprobeFileName);
        if (File.Exists(bundled))
        {
            return bundled;
        }

        if (TryPathDirectories(FfprobeFileName, out var path))
        {
            return path;
        }

        throw new FileNotFoundException(
            "FFprobe was not found next to FFmpeg or on PATH. " +
            "Place ffprobe.exe in the same folder as ffmpeg.exe (e.g. packages/Prototype/ffmpeg/).",
            FfprobeFileName);
    }

    private static bool TryPathDirectories(out string path) => TryPathDirectories(FfmpegFileName, out path);

    private static bool TryPathDirectories(string fileName, out string path)
    {
        var pathEnv = Environment.GetEnvironmentVariable("PATH");
        if (string.IsNullOrEmpty(pathEnv))
        {
            path = string.Empty;
            return false;
        }

        foreach (var dir in pathEnv.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            if (string.IsNullOrWhiteSpace(dir))
            {
                continue;
            }

            var trimmed = dir.Trim('"', ' ');
            var candidate = Path.Combine(trimmed, fileName);
            if (File.Exists(candidate))
            {
                path = candidate;
                return true;
            }

            if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
                && fileName == FfmpegFileName)
            {
                var unixCandidate = Path.Combine(trimmed, "ffmpeg");
                if (File.Exists(unixCandidate))
                {
                    path = unixCandidate;
                    return true;
                }
            }
        }

        path = string.Empty;
        return false;
    }

    private static bool TryBundledPrototypeTools(out string path)
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "packages", "Prototype", "ffmpeg", FfmpegFileName);
            if (File.Exists(candidate))
            {
                path = candidate;
                return true;
            }

            dir = dir.Parent;
        }

        path = string.Empty;
        return false;
    }
}
