using System.Runtime.InteropServices;

namespace SMMPI.Infrastructure.Adb;

/// <summary>
/// Resolves the FFmpeg executable (same discovery pattern as <see cref="AdbLocator"/>).
/// </summary>
public static class FfmpegLocator
{
    private static readonly string FfmpegFileName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "ffmpeg.exe" : "ffmpeg";

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

        throw new FileNotFoundException(
            "FFmpeg was not found. Install FFmpeg, add it to your user PATH, " +
            "or set environment variable SMMPI_FFMPEG to the full path of ffmpeg.exe. " +
            "FFmpeg is required for the H.264 device preview (screenrecord → MJPEG).",
            FfmpegFileName);
    }

    private static bool TryPathDirectories(out string path)
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
            var candidate = Path.Combine(trimmed, FfmpegFileName);
            if (File.Exists(candidate))
            {
                path = candidate;
                return true;
            }

            if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
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
}
