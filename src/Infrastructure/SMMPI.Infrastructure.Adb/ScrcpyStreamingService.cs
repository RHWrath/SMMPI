using System.Diagnostics;
using System.Text;
using SMMPI.Domain.Entities;
using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Adb;

public sealed class ScrcpyStreamingService : IAndroidStreamingService
{
    private readonly IAdbClient _adbClient;
    private readonly IToolPathService _toolPathService;
    private readonly ScrcpyCommandBuilder _commandBuilder;
    private readonly ISessionLogService? _sessionLogService;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private Process? _process;
    private Task? _stdoutDrain;
    private Task<string>? _stderrDrain;
    private string? _currentWindowTitle;
    private AndroidStreamingState _state = new(false, false, null, null, null);

    public ScrcpyStreamingService(
        IAdbClient adbClient,
        IToolPathService toolPathService,
        ScrcpyCommandBuilder? commandBuilder = null,
        ISessionLogService? sessionLogService = null)
    {
        _adbClient = adbClient;
        _toolPathService = toolPathService;
        _commandBuilder = commandBuilder ?? new ScrcpyCommandBuilder();
        _sessionLogService = sessionLogService;
    }

    public event EventHandler<AndroidStreamingState>? StateChanged;

    public AndroidStreamingState State => _state;

    public async Task<OperationResult> StartAsync(AndroidDevice device, AndroidStreamingOptions options, CancellationToken cancellationToken)
    {
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (_process is not null && !_process.HasExited)
            {
                return OperationResult.Fail("Er draait al een scrcpy-stream. Stop de huidige stream voordat je een nieuwe start.");
            }

            _toolPathService.EnsureScrcpyAvailable();
            _ = _toolPathService.ResolveAdbExecutable();
            await _adbClient.EnsureServerAsync(cancellationToken).ConfigureAwait(false);

            var includeAudio = false;
            string? warning = null;
            if (options.AudioEnabled)
            {
                var apiLevel = await GetAndroidApiLevelAsync(device.Serial, cancellationToken).ConfigureAwait(false);
                includeAudio = apiLevel >= 30;
                if (!includeAudio)
                {
                    warning = apiLevel is null
                        ? "Android API-level kon niet worden bepaald. De stream is zonder audio gestart."
                        : $"Audio-forwarding wordt niet ondersteund op Android API {apiLevel}. De stream is zonder audio gestart.";
                }
            }

            var windowTitle = string.IsNullOrWhiteSpace(options.WindowTitle)
                ? $"SMMPI scrcpy {device.Serial} {Guid.NewGuid():N}"
                : options.WindowTitle;
            var effectiveOptions = options with { WindowTitle = windowTitle };
            var process = StartScrcpyProcess(device.Serial, effectiveOptions, includeAudio);

            _process = process;
            _currentWindowTitle = windowTitle;
            _stdoutDrain = process.StandardOutput.BaseStream.CopyToAsync(Stream.Null, CancellationToken.None);
            _stderrDrain = ReadToEndAsync(process.StandardError, CancellationToken.None);
            process.EnableRaisingEvents = true;
            process.Exited += (_, _) => PublishStoppedState();

            PublishState(new AndroidStreamingState(
                true,
                !string.IsNullOrWhiteSpace(effectiveOptions.RecordPath),
                process.Id,
                windowTitle,
                warning));
            if (_sessionLogService is not null)
            {
                await _sessionLogService.LogAsync(
                    string.IsNullOrWhiteSpace(effectiveOptions.RecordPath)
                        ? $"scrcpy stream started for {device.Serial}"
                        : $"scrcpy recording stream started for {device.Serial}: {effectiveOptions.RecordPath}",
                    cancellationToken).ConfigureAwait(false);
            }

            return OperationResult.Ok(warning ?? "scrcpy-stream gestart.");
        }
        catch (Exception ex)
        {
            await StopCurrentProcessAsync(TimeSpan.FromSeconds(2), CancellationToken.None, allowKill: true).ConfigureAwait(false);
            PublishState(new AndroidStreamingState(false, false, null, null, ex.Message));
            return OperationResult.Fail(ex.Message);
        }
        finally
        {
            _gate.Release();
        }
    }

    public async Task StopAsync(CancellationToken cancellationToken)
    {
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var timeout = _state.IsRecording ? TimeSpan.FromSeconds(30) : TimeSpan.FromSeconds(5);
            await StopCurrentProcessAsync(timeout, cancellationToken, allowKill: !_state.IsRecording).ConfigureAwait(false);
            PublishState(new AndroidStreamingState(false, false, null, null, null));
            if (_sessionLogService is not null)
            {
                await _sessionLogService.LogAsync("scrcpy stream stopped", cancellationToken).ConfigureAwait(false);
            }
        }
        finally
        {
            _gate.Release();
        }
    }

    public async ValueTask DisposeAsync()
    {
        await StopAsync(CancellationToken.None).ConfigureAwait(false);
        _gate.Dispose();
    }

    private Process StartScrcpyProcess(string serial, AndroidStreamingOptions options, bool includeAudio)
    {
        var process = new Process
        {
            StartInfo =
            {
                FileName = _toolPathService.ResolveScrcpyExecutable(),
                WorkingDirectory = _toolPathService.ResolveScrcpyDirectory(),
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            },
        };

        foreach (var arg in _commandBuilder.BuildArguments(serial, options, includeAudio))
        {
            process.StartInfo.ArgumentList.Add(arg);
        }

        if (!process.Start())
        {
            throw new InvalidOperationException("scrcpy kon niet worden gestart.");
        }

        return process;
    }

    private async Task<int?> GetAndroidApiLevelAsync(string serial, CancellationToken cancellationToken)
    {
        try
        {
            var value = await _adbClient.ShellAsync(serial, "getprop ro.build.version.sdk", cancellationToken).ConfigureAwait(false);
            return int.TryParse(value.Trim(), System.Globalization.NumberStyles.Integer, System.Globalization.CultureInfo.InvariantCulture, out var apiLevel)
                ? apiLevel
                : null;
        }
        catch
        {
            return null;
        }
    }

    private async Task StopCurrentProcessAsync(TimeSpan timeout, CancellationToken cancellationToken, bool allowKill)
    {
        var process = _process;
        var windowTitle = _currentWindowTitle;
        if (process is null)
        {
            return;
        }

        try
        {
            if (!process.HasExited)
            {
                try
                {
                    process.Refresh();
                    process.CloseMainWindow();
                }
                catch
                {
                }

                try
                {
                    _ = NativeWindowCloser.CloseWindowsForProcess(process.Id, windowTitle);
                }
                catch
                {
                }

                if (!await WaitForExitAsync(process, timeout, cancellationToken).ConfigureAwait(false))
                {
                    if (!allowKill)
                    {
                        throw new TimeoutException(
                            "scrcpy is niet op tijd netjes gestopt. De opname is niet geforceerd afgebroken, omdat dat een MP4 kan beschadigen. Probeer de stream nogmaals te stoppen.");
                    }

                    process.Kill(entireProcessTree: true);
                    await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
                }
            }

            if (_stdoutDrain is not null)
            {
                try
                {
                    await _stdoutDrain.WaitAsync(TimeSpan.FromSeconds(1), CancellationToken.None).ConfigureAwait(false);
                }
                catch
                {
                }
            }
        }
        catch
        {
            if (!allowKill)
            {
                throw;
            }

            try
            {
                if (!process.HasExited)
                {
                    process.Kill(entireProcessTree: true);
                }
            }
            catch
            {
            }
        }
        finally
        {
            if (process.HasExited)
            {
                _process = null;
                _currentWindowTitle = null;
                process.Dispose();
                _stdoutDrain = null;
                _stderrDrain = null;
            }
        }
    }

    private static async Task<bool> WaitForExitAsync(Process process, TimeSpan timeout, CancellationToken cancellationToken)
    {
        try
        {
            await process.WaitForExitAsync(cancellationToken).WaitAsync(timeout, cancellationToken).ConfigureAwait(false);
            return true;
        }
        catch (TimeoutException)
        {
            return false;
        }
    }

    private static async Task<string> ReadToEndAsync(StreamReader reader, CancellationToken cancellationToken)
    {
        var builder = new StringBuilder();
        var buffer = new char[4096];
        while (true)
        {
            var read = await reader.ReadAsync(buffer.AsMemory(0, buffer.Length), cancellationToken).ConfigureAwait(false);
            if (read == 0)
            {
                return builder.ToString();
            }

            builder.Append(buffer, 0, read);
        }
    }

    private void PublishStoppedState()
    {
        if (_process is null)
        {
            return;
        }

        PublishState(new AndroidStreamingState(false, false, null, null, "scrcpy-stream is gestopt."));
    }

    private void PublishState(AndroidStreamingState state)
    {
        _state = state;
        StateChanged?.Invoke(this, state);
    }
}
