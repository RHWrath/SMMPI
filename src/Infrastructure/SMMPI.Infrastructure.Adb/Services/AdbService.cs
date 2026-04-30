using SMMPI.Domain.Entities;
using System.ComponentModel;
using System.Diagnostics;

namespace SMMPI.Infrastructure.Adb.Services;

public class AdbService
{
    public async Task<bool> IsAdbAvailableAsync(CancellationToken cancellationToken = default)
    {
        var result = await RunAdbTextCommandAsync("verion", cancellationToken);
        return result.ExitCode == 0;
    }

    public async Task<IReadOnlyList<AndroidDevice>> GetDevicesAsync(CancellationToken cancellationToken = default)
    {
        var result = await RunAdbTextCommandAsync("devices", cancellationToken);

        if (result.ExitCode != 0)
        {
            throw new InvalidOperationException(string.IsNullOrWhiteSpace(result.StandardError)
                ? "Kon devices niet ophalen via ADB"
                : result.StandardError.Trim());
        }

        var devices = new List<AndroidDevice>();
        var lines = result.StandardOutput
            .Split(new[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries)
            .Skip(1);

        foreach (var line in lines) 
        {
            var parts = line
                .Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);

            if (parts.Length < 2)
            {
                continue;
            }

            devices.Add(new AndroidDevice
            {
                Serial = parts[0],
                State = parts[1],
            });
        }

        return devices;
    }

    public async Task<byte[]> CaptureScreenAsync(CancellationToken cancellationToken = default)
    {
        var result = await RunAdbBinaryCommandAsync("exec-out screencap -p", cancellationToken);

        if (result.ExitCode != 0)
        {
            throw new InvalidOperationException(GetFriendlyAdbError(result.StandardError));
        }

        if (result.Output.Length == 0)
        {
            throw new InvalidOperationException("Lege screenshot ontvangen via ADB.");
        }

        return result.Output;
    }

    private async Task<AdbTextResult> RunAdbTextCommandAsync(string arguments, CancellationToken cancellationToken)
    {
        var startInfo = CreateAdbProcessStartInfo(arguments);

        using var process = new Process { StartInfo = startInfo };

        try
        {
            process.Start();
        }
        catch (Win32Exception ex)
        {
            throw new InvalidOperationException("ADB niet gevonden. Installeer Android Platform-tools en zet adb in PATH.", ex);
        }

        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);

        await process.WaitForExitAsync(cancellationToken);

        return new AdbTextResult(
            process.ExitCode,
            await stdoutTask,
            await stderrTask);
    }

    private async Task<AdbBinaryResult> RunAdbBinaryCommandAsync(string arguments, CancellationToken cancellationToken)
    {
        var startInfo = CreateAdbProcessStartInfo(arguments);

        using var process = new Process { StartInfo = startInfo };

        try
        {
            process.Start();
        }
        catch (Win32Exception ex)
        {
            throw new InvalidOperationException("ADB niet gevonden. Installeer Android Platform-tools en zet adb in PATH.", ex);
        }

        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);

        await using var memoryStream = new MemoryStream();
        await process.StandardOutput.BaseStream.CopyToAsync(memoryStream, cancellationToken);

        await process.WaitForExitAsync(cancellationToken);

        return new AdbBinaryResult(
            process.ExitCode,
            memoryStream.ToArray(),
            await stderrTask);
    }

    private static ProcessStartInfo CreateAdbProcessStartInfo(string arguments)
    {
        return new ProcessStartInfo
        {
            FileName = "adb",
            Arguments = arguments,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8,
            StandardErrorEncoding = System.Text.Encoding.UTF8,
        };
    }

    private static string GetFriendlyAdbError(string? adbError)
    {
        var error = adbError?.Trim() ?? string.Empty;

        if (string.IsNullOrWhiteSpace(error))
        {
            return "ADB-commando is mislukt zonder foutmelding";
        }

        if (error.Contains("unauthorized", StringComparison.OrdinalIgnoreCase))
        {
            return "Device unauthorized. Accepteer USB debugging op je telefoon en probeer opnieuw";
        }

        if (error.Contains("no devices/emulators found", StringComparison.OrdinalIgnoreCase))
        {
            return "Geen device gevonden";
        }

        return error;
    }

    private readonly record struct AdbTextResult(int ExitCode, string StandardOutput, string StandardError);
    private readonly record struct AdbBinaryResult(int ExitCode, byte[] Output, string StandardError);
}
