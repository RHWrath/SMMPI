using SMMPI.Domain.Entities;
using SMMPI.Domain.Interfaces;
using System.Diagnostics;
using System.Text;

namespace SMMPI.Infrastructure.Adb;

public sealed class FfmpegStreamRecordingService : IStreamRecordingService
{
    private const int FramesPerSecond = 30;
    private readonly IDeviceStreamService _streamService;
    private readonly string _ffmpegPath;
    private readonly object _sync = new();
    private RecordingSession? _session;
    private StreamFrame? _latestFrame;
    private Process? _process;
    private CancellationTokenSource? _recordingCancellation;
    private Task? _writerTask;
    private Task<string>? _stderrTask;
    private string? _currentOutputPath;

    public FfmpegStreamRecordingService(IDeviceStreamService streamService, string? ffmpegExecutable = null)
    {
        _streamService = streamService;
        _ffmpegPath = string.IsNullOrWhiteSpace(ffmpegExecutable) ? FfmpegLocator.Resolve() : ffmpegExecutable.Trim();
        _streamService.FrameReceived += OnFrameReceived;
    }

    public bool IsRecording { get; private set; }

    public Task StartSessionAsync(string officerName, string caseNumber, string caseRoot, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(caseNumber))
        {
            throw new ArgumentException("Case number is required.", nameof(caseNumber));
        }

        if (string.IsNullOrWhiteSpace(caseRoot))
        {
            throw new ArgumentException("Case root is required.", nameof(caseRoot));
        }

        var caseFolder = Path.Combine(caseRoot, caseNumber);
        Directory.CreateDirectory(caseFolder);
        _session = new RecordingSession(officerName, caseNumber, caseRoot, caseFolder);
        return Task.CompletedTask;
    }

    public Task StartRecordingAsync(string platformName, CancellationToken cancellationToken)
    {
        if (IsRecording)
        {
            throw new InvalidOperationException("Recording is already running.");
        }

        var session = _session ?? throw new InvalidOperationException("No recording session has been configured.");
        var firstFrame = GetLatestFrame() ?? throw new InvalidOperationException("No stream frame has been received yet.");
        if (firstFrame.Width <= 0 || firstFrame.Height <= 0 || firstFrame.ImageBytes.Length == 0)
        {
            throw new InvalidOperationException("The latest stream frame is empty.");
        }

        Directory.CreateDirectory(session.CaseFolder);
        var safePlatform = SanitizeName(platformName);
        var timestamp = DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss", System.Globalization.CultureInfo.InvariantCulture);
        _currentOutputPath = Path.Combine(session.CaseFolder, $"{safePlatform}_{timestamp}.mp4");

        _process = StartFfmpeg(_currentOutputPath);
        _stderrTask = _process.StandardError.ReadToEndAsync(cancellationToken);
        _recordingCancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        IsRecording = true;
        _writerTask = Task.Run(() => WriteFramesAsync(_process, _recordingCancellation.Token), CancellationToken.None);
        return Task.CompletedTask;
    }

    public async Task<string?> StopRecordingAsync(CancellationToken cancellationToken)
    {
        if (!IsRecording)
        {
            throw new InvalidOperationException("No recording is currently running.");
        }

        var process = _process;
        var outputPath = _currentOutputPath;
        IsRecording = false;
        _recordingCancellation?.Cancel();

        try
        {
            if (process is not null)
            {
                await process.StandardInput.BaseStream.FlushAsync(cancellationToken).ConfigureAwait(false);
                process.StandardInput.Close();
            }
        }
        catch
        {
        }

        if (_writerTask is not null)
        {
            try
            {
                await _writerTask.WaitAsync(TimeSpan.FromSeconds(3), cancellationToken).ConfigureAwait(false);
            }
            catch
            {
            }
        }

        if (process is not null)
        {
            if (!await WaitForExitAsync(process, TimeSpan.FromSeconds(10), cancellationToken).ConfigureAwait(false))
            {
                TryKill(process);
                await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
            }

            var stderr = await ReadStderrAsync(cancellationToken).ConfigureAwait(false);
            if (process.ExitCode != 0)
            {
                throw new InvalidOperationException($"FFmpeg recording failed: {stderr}".Trim());
            }
        }

        CleanupRecordingState();
        return File.Exists(outputPath) ? outputPath : null;
    }

    public async ValueTask DisposeAsync()
    {
        _streamService.FrameReceived -= OnFrameReceived;
        if (IsRecording)
        {
            try
            {
                await StopRecordingAsync(CancellationToken.None).ConfigureAwait(false);
            }
            catch
            {
            }
        }

        CleanupRecordingState();
    }

    public static string SanitizeName(string value)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var cleaned = new StringBuilder(value.Length);
        foreach (var c in value.Trim())
        {
            cleaned.Append(invalid.Contains(c) ? '_' : c);
        }

        var result = cleaned.ToString();
        return string.IsNullOrWhiteSpace(result) ? "recording" : result;
    }

    private void OnFrameReceived(object? sender, StreamFrame frame)
    {
        if (frame.ImageBytes.Length == 0 || frame.Width <= 0 || frame.Height <= 0)
        {
            return;
        }

        lock (_sync)
        {
            _latestFrame = frame;
        }
    }

    private StreamFrame? GetLatestFrame()
    {
        lock (_sync)
        {
            return _latestFrame;
        }
    }

    private Process StartFfmpeg(string outputPath) 
    { 
        var process = new Process 
        { 
            StartInfo = 
            { 
                FileName = _ffmpegPath, 
                UseShellExecute = false, 
                RedirectStandardInput = true, 
                RedirectStandardError = true, 
                RedirectStandardOutput = true, 
                CreateNoWindow = true, 
            }, 
        };
        
        process.StartInfo.ArgumentList.Add("-hide_banner"); 
        process.StartInfo.ArgumentList.Add("-loglevel");
        process.StartInfo.ArgumentList.Add("error");
        process.StartInfo.ArgumentList.Add("-y");
        process.StartInfo.ArgumentList.Add("-f");
        process.StartInfo.ArgumentList.Add("image2pipe");
        process.StartInfo.ArgumentList.Add("-framerate");
        process.StartInfo.ArgumentList.Add(FramesPerSecond.ToString(System.Globalization.CultureInfo.InvariantCulture));
        process.StartInfo.ArgumentList.Add("-i"); process.StartInfo.ArgumentList.Add("-");
        process.StartInfo.ArgumentList.Add("-an"); process.StartInfo.ArgumentList.Add("-c:v");
        process.StartInfo.ArgumentList.Add("libx264"); process.StartInfo.ArgumentList.Add("-preset");
        process.StartInfo.ArgumentList.Add("veryfast"); process.StartInfo.ArgumentList.Add("-pix_fmt");
        process.StartInfo.ArgumentList.Add("yuv420p"); process.StartInfo.ArgumentList.Add("-movflags");
        process.StartInfo.ArgumentList.Add("+faststart"); process.StartInfo.ArgumentList.Add(outputPath);

        if (!process.Start())
        { 
            throw new InvalidOperationException("FFmpeg recording process could not be started.");
        } 
        _ = process.StandardOutput.BaseStream.CopyToAsync(Stream.Null); return process;
    }

    private async Task WriteFramesAsync(Process process, CancellationToken cancellationToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(1d / FramesPerSecond));
        while (await timer.WaitForNextTickAsync(cancellationToken).ConfigureAwait(false))
        {
            if (process.HasExited)
            {
                return;
            }

            var frame = GetLatestFrame();
            if (frame is null)
            {
                continue;
            }

            await process.StandardInput.BaseStream.WriteAsync(frame.ImageBytes, cancellationToken).ConfigureAwait(false);
        }
    }

    private async Task<string> ReadStderrAsync(CancellationToken cancellationToken)
    {
        if (_stderrTask is null)
        {
            return string.Empty;
        }

        try
        {
            return await _stderrTask.WaitAsync(cancellationToken).ConfigureAwait(false);
        }
        catch
        {
            return string.Empty;
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

    private void CleanupRecordingState()
    {
        _recordingCancellation?.Dispose();
        _recordingCancellation = null;
        _writerTask = null;
        _stderrTask = null;
        _process?.Dispose();
        _process = null;
        _currentOutputPath = null;
        IsRecording = false;
    }

    private static void TryKill(Process process)
    {
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

    private sealed record RecordingSession(string OfficerName, string CaseNumber, string CaseRoot, string CaseFolder);
}
