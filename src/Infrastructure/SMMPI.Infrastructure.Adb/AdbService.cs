using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;
using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Adb;

public sealed class AdbService : IAdbClient
{
    private readonly AdbCommandRunner _runner;
    private readonly AdbCommandBuilder _builder;
    /// <summary>Serializes all ADB transport so screencap and <c>input</c> never run concurrently (avoids USB/server contention and dropped touches).</summary>
    private readonly SemaphoreSlim _adbGate = new(1, 1);

    public AdbService()
        : this(new AdbCommandRunner(), new AdbCommandBuilder())
    {
    }

    public AdbService(AdbCommandRunner runner, AdbCommandBuilder builder)
    {
        _runner = runner;
        _builder = builder;
    }

    public async Task EnsureServerAsync(CancellationToken cancellationToken)
    {
        await _adbGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var result = await _runner.RunAsync(_builder.BuildStartServer(), cancellationToken).ConfigureAwait(false);
            EnsureSuccess(result, "ADB server could not be started.");
        }
        finally
        {
            _adbGate.Release();
        }
    }

    public async Task<IReadOnlyList<AndroidDevice>> GetDevicesAsync(CancellationToken cancellationToken)
    {
        await _adbGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var result = await _runner.RunAsync(_builder.BuildDevices(), cancellationToken).ConfigureAwait(false);
            EnsureSuccess(result, "ADB device list could not be read.");

            var devices = new List<AndroidDevice>();
            foreach (var line in result.StandardOutput.Split(Environment.NewLine, StringSplitOptions.RemoveEmptyEntries).Skip(1))
            {
                var parts = line.Trim().Split(null as char[], StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length < 2)
                {
                    continue;
                }

                var serial = parts[0];
                var state = parts[1] switch
                {
                    "device" => DeviceConnectionState.Connected,
                    "unauthorized" => DeviceConnectionState.Unauthorized,
                    "offline" => DeviceConnectionState.Offline,
                    _ => DeviceConnectionState.Unknown
                };

                devices.Add(new AndroidDevice(serial, string.Empty, serial, string.Empty, state));
            }

            for (var i = 0; i < devices.Count; i++)
            {
                if (devices[i].State != DeviceConnectionState.Connected)
                {
                    continue;
                }

                var manufacturer = await ExecuteShellAsync(devices[i].Serial, "getprop ro.product.manufacturer", cancellationToken).ConfigureAwait(false);
                var model = await ExecuteShellAsync(devices[i].Serial, "getprop ro.product.model", cancellationToken).ConfigureAwait(false);
                var androidVersion = await ExecuteShellAsync(devices[i].Serial, "getprop ro.build.version.release", cancellationToken).ConfigureAwait(false);
                devices[i] = devices[i] with
                {
                    Manufacturer = manufacturer.Trim(),
                    Model = model.Trim(),
                    AndroidVersion = androidVersion.Trim()
                };
            }

            return devices;
        }
        finally
        {
            _adbGate.Release();
        }
    }

    public async Task<string> ShellAsync(string serial, string command, CancellationToken cancellationToken)
    {
        await _adbGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            return await ExecuteShellAsync(serial, command, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _adbGate.Release();
        }
    }

    public async Task PushAsync(string serial, string localPath, string remotePath, CancellationToken cancellationToken)
    {
        await _adbGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var result = await _runner.RunAsync(_builder.BuildPush(serial, localPath, remotePath), cancellationToken).ConfigureAwait(false);
            EnsureSuccess(result, $"Failed to push {Path.GetFileName(localPath)} to device.");
        }
        finally
        {
            _adbGate.Release();
        }
    }

    public async Task SendTouchAsync(string serial, TouchAction action, int x, int y, CancellationToken cancellationToken)
    {
        await _adbGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var result = await _runner.RunAsync(_builder.BuildTouch(serial, action, x, y), cancellationToken).ConfigureAwait(false);
            EnsureSuccess(result, $"Failed to send touch event {action}.");
        }
        finally
        {
            _adbGate.Release();
        }
    }

    public async Task<byte[]> CaptureScreenAsync(string serial, CancellationToken cancellationToken)
    {
        await _adbGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            return await _runner.RunBinaryAsync(_builder.BuildScreencap(serial), cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _adbGate.Release();
        }
    }

    public async Task SendKeyEventAsync(string serial, int androidKeyCode, CancellationToken cancellationToken)
    {
        await _adbGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var args = new[]
            {
                "-s",
                serial,
                "shell",
                "input",
                "keyevent",
                androidKeyCode.ToString(System.Globalization.CultureInfo.InvariantCulture)
            };
            var result = await _runner.RunWithArgumentListAsync(_builder.AdbExecutable, args, cancellationToken).ConfigureAwait(false);
            EnsureSuccess(result, $"Failed to send key event {androidKeyCode}.");
        }
        finally
        {
            _adbGate.Release();
        }
    }

    public async Task SendTextAsync(string serial, string text, CancellationToken cancellationToken)
    {
        if (string.IsNullOrEmpty(text))
        {
            return;
        }

        foreach (var chunk in AndroidInputTextEncoder.EncodeToChunks(text))
        {
            await _adbGate.WaitAsync(cancellationToken).ConfigureAwait(false);
            try
            {
                var args = new[] { "-s", serial, "shell", "input", "text", chunk };
                var result = await _runner.RunWithArgumentListAsync(_builder.AdbExecutable, args, cancellationToken).ConfigureAwait(false);
                EnsureSuccess(result, "Failed to send text to device.");
            }
            finally
            {
                _adbGate.Release();
            }
        }
    }

    private async Task<string> ExecuteShellAsync(string serial, string command, CancellationToken cancellationToken)
    {
        var result = await _runner.RunAsync(_builder.BuildShell(serial, command), cancellationToken).ConfigureAwait(false);
        EnsureSuccess(result, $"ADB shell command failed: {command}");
        return result.StandardOutput.Trim();
    }

    private static void EnsureSuccess(AdbCommandResult result, string message)
    {
        if (!result.Success)
        {
            throw new InvalidOperationException($"{message}{Environment.NewLine}{result.StandardError}{result.StandardOutput}");
        }
    }
}
