using System.IO;
using AdvancedSharpAdbClient;
using AdvancedSharpAdbClient.Models;
using AdvancedSharpAdbClient.Receivers;

namespace WPFTest.Services;

/// <summary>
/// Starts the ADB server when possible and exposes device listing / shell (AdvancedSharpAdbClient).
/// </summary>
internal sealed class AdbConnectionService
{
    private readonly AdbClient _client = new();

    /// <summary>
    /// Ensures <c>adb</c> server is running. Returns an error message for the UI, or null on success.
    /// </summary>
    public string? TryEnsureAdbServerStarted()
    {
        var adbPath = ResolveAdbExecutablePath();
        if (adbPath is null)
        {
            return "adb.exe not found. Install Android Platform Tools and add them to PATH, or set ANDROID_HOME.";
        }

        try
        {
            if (!AdbServer.Instance.GetStatus().IsRunning)
            {
                var server = new AdbServer();
                var result = server.StartServer(adbPath, restartServerIfNewer: false);
                if (result != StartServerResult.Started && result != StartServerResult.AlreadyRunning)
                {
                    return $"Could not start ADB server (result: {result}).";
                }
            }
        }
        catch (Exception ex)
        {
            return ex.Message;
        }

        return null;
    }

    public IReadOnlyList<DeviceData> GetDevices() =>
        _client.GetDevices().Where(d => d.State == DeviceState.Online).ToList();

    public string ExecuteShell(DeviceData device, string command)
    {
        var receiver = new ConsoleOutputReceiver();
        _client.ExecuteRemoteCommand(command, device, receiver);
        return receiver.ToString() ?? string.Empty;
    }

    public string? GetDeviceDisplayName(DeviceData device)
    {
        try
        {
            var model = ExecuteShell(device, "getprop ro.product.model").Trim();
            var manufacturer = ExecuteShell(device, "getprop ro.product.manufacturer").Trim();
            if (!string.IsNullOrEmpty(manufacturer) && !string.IsNullOrEmpty(model))
            {
                return $"{manufacturer} {model} ({device.Serial})";
            }
        }
        catch
        {
            // ignore and fall back
        }

        return device.Serial;
    }

    private static string? ResolveAdbExecutablePath()
    {
        var home = Environment.GetEnvironmentVariable("ANDROID_HOME")
                   ?? Environment.GetEnvironmentVariable("ANDROID_SDK_ROOT");
        if (!string.IsNullOrWhiteSpace(home))
        {
            var candidate = Path.Combine(home, "platform-tools", "adb.exe");
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }

        var pathEnv = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        foreach (var dir in pathEnv.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            var trimmed = dir.Trim().Trim('"');
            var candidate = Path.Combine(trimmed, "adb.exe");
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }

        return null;
    }
}
