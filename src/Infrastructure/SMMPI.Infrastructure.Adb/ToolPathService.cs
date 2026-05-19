using System.Runtime.InteropServices;
using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Adb;

public sealed class ToolPathService : IToolPathService
{
    private static readonly string AdbFileName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "adb.exe" : "adb";
    private static readonly string ScrcpyFileName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "scrcpy.exe" : "scrcpy";

    public string ResolveAdbExecutable()
    {
        var explicitPath = Environment.GetEnvironmentVariable("SMMPI_ADB");
        if (TryExplicitFile(explicitPath, out var path))
        {
            return path;
        }

        if (TryBundledToolsFile(AdbFileName, out path))
        {
            return path;
        }

        return AdbLocator.Resolve();
    }

    public string ResolveScrcpyExecutable()
    {
        var explicitPath = Environment.GetEnvironmentVariable("SMMPI_SCRCPY");
        if (TryExplicitFile(explicitPath, out var path))
        {
            return path;
        }

        if (TryBundledToolsFile(ScrcpyFileName, out path))
        {
            return path;
        }

        if (TryPathDirectories(ScrcpyFileName, out path))
        {
            return path;
        }

        throw new FileNotFoundException(
            "scrcpy was not found. Place the full scrcpy distribution in the repository tools folder, " +
            "add scrcpy to PATH, or set SMMPI_SCRCPY to the full path of scrcpy.exe.",
            ScrcpyFileName);
    }

    public string ResolveScrcpyDirectory() => Path.GetDirectoryName(ResolveScrcpyExecutable())
        ?? throw new InvalidOperationException("Could not resolve the scrcpy directory.");

    public void EnsureScrcpyAvailable()
    {
        var dir = ResolveScrcpyDirectory();
        var required = new List<string> { ScrcpyFileName, "scrcpy-server" };
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            required.AddRange(["SDL3.dll", "adb.exe"]);
        }

        var missing = required
            .Where(file => !File.Exists(Path.Combine(dir, file)))
            .ToArray();

        if (missing.Length > 0)
        {
            throw new FileNotFoundException(
                $"The scrcpy folder is incomplete. Missing: {string.Join(", ", missing)}. " +
                $"Expected a full scrcpy distribution in {dir}.");
        }
    }

    private static bool TryExplicitFile(string? value, out string path)
    {
        if (!string.IsNullOrWhiteSpace(value) && File.Exists(value.Trim()))
        {
            path = Path.GetFullPath(value.Trim());
            return true;
        }

        path = string.Empty;
        return false;
    }

    private static bool TryBundledToolsFile(string fileName, out string path)
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "tools", fileName);
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

            var candidate = Path.Combine(dir.Trim('"', ' '), fileName);
            if (File.Exists(candidate))
            {
                path = candidate;
                return true;
            }
        }

        path = string.Empty;
        return false;
    }
}
