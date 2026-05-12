using System.Runtime.InteropServices;

namespace SMMPI.Infrastructure.Adb;

/// <summary>
/// Resolves the ADB executable. IDE-launched apps often do not inherit the same PATH as an interactive shell,
/// so relying on <c>FileName="adb"</c> alone frequently fails on Windows.
/// </summary>
public static class AdbLocator
{
    private static readonly string AdbFileName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "adb.exe" : "adb";

    /// <summary>
    /// Returns an absolute path to the ADB executable, or throws <see cref="FileNotFoundException"/>.
    /// </summary>
    public static string Resolve()
    {
        var explicitPath = Environment.GetEnvironmentVariable("SMMPI_ADB");
        if (!string.IsNullOrWhiteSpace(explicitPath) && File.Exists(explicitPath.Trim()))
        {
            return Path.GetFullPath(explicitPath.Trim());
        }

        if (TryPathFromEnvironmentSdk(out var path))
        {
            return path;
        }

        if (TryDefaultWindowsUserSdk(out path))
        {
            return path;
        }

        if (TryPathDirectories(out path))
        {
            return path;
        }

        throw new FileNotFoundException(
            "ADB was not found. Install Android platform-tools, add its folder to your user PATH, " +
            "set ANDROID_HOME or ANDROID_SDK_ROOT to your Android SDK root, " +
            "or set environment variable SMMPI_ADB to the full path of adb.exe. " +
            "(The app does not use the shell PATH alone so it still works when launched from an IDE.)",
            AdbFileName);
    }

    private static bool TryPathFromEnvironmentSdk(out string path)
    {
        foreach (var root in new[]
                 {
                     Environment.GetEnvironmentVariable("ANDROID_HOME"),
                     Environment.GetEnvironmentVariable("ANDROID_SDK_ROOT")
                 })
        {
            if (string.IsNullOrWhiteSpace(root))
            {
                continue;
            }

            var candidate = Path.Combine(root.Trim(), "platform-tools", AdbFileName);
            if (File.Exists(candidate))
            {
                path = candidate;
                return true;
            }
        }

        path = string.Empty;
        return false;
    }

    private static bool TryDefaultWindowsUserSdk(out string path)
    {
        path = string.Empty;
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            return false;
        }

        var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        var candidate = Path.Combine(localAppData, "Android", "Sdk", "platform-tools", AdbFileName);
        if (File.Exists(candidate))
        {
            path = candidate;
            return true;
        }

        return false;
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
            var candidate = Path.Combine(trimmed, AdbFileName);
            if (File.Exists(candidate))
            {
                path = candidate;
                return true;
            }

            if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                var unixCandidate = Path.Combine(trimmed, "adb");
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
