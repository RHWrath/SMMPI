using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;
using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Adb;

public sealed class AdbPlatformDetectionService : IPlatformDetectionService
{
    private static readonly IReadOnlyDictionary<string, PlatformTarget> KnownPlatforms =
        new Dictionary<string, PlatformTarget>(StringComparer.Ordinal)
        {
            ["com.snapchat.android"] = new(
                "Snapchat",
                "com.snapchat.android",
                DeviceProfile.SnapchatDefault),
            ["com.whatsapp"] = new(
                "WhatsApp",
                "com.whatsapp",
                new DeviceProfile(
                    "WhatsApp",
                    "/storage/emulated/0/Android/data/com.whatsapp/files/Camera1/",
                    "virtual.mp4",
                    1920,
                    1080,
                    30,
                    TimeSpan.FromSeconds(60),
                    TimeSpan.FromSeconds(10),
                    MediaTransform.None)),
            ["com.discord"] = new(
                "Discord",
                "com.discord",
                new DeviceProfile(
                    "Discord",
                    "/storage/emulated/0/Android/data/com.discord/files/Camera1/",
                    "virtual.mp4",
                    1920,
                    1080,
                    30,
                    TimeSpan.FromSeconds(60),
                    TimeSpan.FromSeconds(10),
                    MediaTransform.None)),
        };

    private readonly IAdbClient _adbClient;

    public AdbPlatformDetectionService(IAdbClient adbClient)
    {
        _adbClient = adbClient;
    }

    public async Task<PlatformTarget?> GetActivePlatformAsync(string serial, CancellationToken cancellationToken)
    {
        var output = await _adbClient.ShellAsync(serial, "dumpsys activity activities", cancellationToken).ConfigureAwait(false);
        var packageName = ParseForegroundPackage(output);
        return packageName is not null && KnownPlatforms.TryGetValue(packageName, out var platform)
            ? platform
            : null;
    }

    public static string? ParseForegroundPackage(string output)
    {
        foreach (var line in output.Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            if (!line.Contains("ResumedActivity", StringComparison.Ordinal))
            {
                continue;
            }

            foreach (var part in line.Split(' ', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
            {
                if (!part.Contains('/', StringComparison.Ordinal) || !part.Contains('.', StringComparison.Ordinal))
                {
                    continue;
                }

                var package = part.Split('/')[0];
                if (package.Length > 0 && !package.Contains('{', StringComparison.Ordinal) && !package.Contains('}', StringComparison.Ordinal) && !package.Contains(':', StringComparison.Ordinal))
                {
                    return package;
                }
            }
        }

        return null;
    }
}
