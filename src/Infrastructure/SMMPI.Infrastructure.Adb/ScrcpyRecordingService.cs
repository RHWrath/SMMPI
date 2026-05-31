using SMMPI.Domain.Entities;
using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Adb;

public sealed class ScrcpyRecordingService : IRecordingService
{
    private readonly IAndroidStreamingService _streamingService;
    private readonly Sha256FileHasher _hasher;
    private readonly ISessionLogService? _sessionLogService;
    private RecordingSession? _session;
    private AndroidDevice? _recordingDevice;
    private string? _currentOutputPath;
    private bool _recordingAudioEnabled;

    public ScrcpyRecordingService(
        IAndroidStreamingService streamingService,
        Sha256FileHasher? hasher = null,
        ISessionLogService? sessionLogService = null)
    {
        _streamingService = streamingService;
        _hasher = hasher ?? new Sha256FileHasher();
        _sessionLogService = sessionLogService;
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

    public async Task<OperationResult> StartRecordingAsync(AndroidDevice device, string platformName, bool audioEnabled, CancellationToken cancellationToken)
    {
        if (IsRecording)
        {
            return OperationResult.Fail("Er loopt al een opname.");
        }

        var session = _session ?? throw new InvalidOperationException("No recording session has been configured.");
        Directory.CreateDirectory(session.CaseFolder);

        var timestamp = DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss", System.Globalization.CultureInfo.InvariantCulture);
        var outputPath = Path.Combine(session.CaseFolder, $"{SanitizeName(platformName)}_{timestamp}.mp4");

        await _streamingService.StopAsync(cancellationToken).ConfigureAwait(false);
        var result = await _streamingService.StartAsync(
            device,
            new AndroidStreamingOptions(AudioEnabled: audioEnabled, RecordPath: outputPath),
            cancellationToken).ConfigureAwait(false);

        if (!result.Success)
        {
            return result;
        }

        IsRecording = true;
        _recordingDevice = device;
        _recordingAudioEnabled = audioEnabled;
        _currentOutputPath = outputPath;
        if (_sessionLogService is not null)
        {
            await _sessionLogService.LogAsync($"Recording started: {outputPath}", cancellationToken).ConfigureAwait(false);
        }

        return OperationResult.Ok(result.Message);
    }

    public async Task<RecordingResult?> StopRecordingAsync(CancellationToken cancellationToken)
    {
        if (!IsRecording)
        {
            throw new InvalidOperationException("No recording is currently running.");
        }

        var outputPath = _currentOutputPath;
        var device = _recordingDevice;
        var audioEnabled = _recordingAudioEnabled;

        await _streamingService.StopAsync(cancellationToken).ConfigureAwait(false);

        IsRecording = false;
        _currentOutputPath = null;
        _recordingDevice = null;
        _recordingAudioEnabled = false;

        if (device is not null)
        {
            await _streamingService.StartAsync(device, new AndroidStreamingOptions(AudioEnabled: audioEnabled), cancellationToken).ConfigureAwait(false);
        }

        if (string.IsNullOrWhiteSpace(outputPath) || !File.Exists(outputPath))
        {
            return null;
        }

        var hash = await _hasher.ComputeAsync(outputPath, cancellationToken).ConfigureAwait(false);
        if (_sessionLogService is not null)
        {
            await _sessionLogService.LogAsync($"Recording stopped: {outputPath} SHA-256={hash}", cancellationToken).ConfigureAwait(false);
        }

        return new RecordingResult(outputPath, hash);
    }

    public async ValueTask DisposeAsync()
    {
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
    }

    public static string SanitizeName(string value)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var cleaned = new string(value.Trim().Select(c => invalid.Contains(c) ? '_' : c).ToArray());
        return string.IsNullOrWhiteSpace(cleaned) ? "recording" : cleaned;
    }

    private sealed record RecordingSession(string OfficerName, string CaseNumber, string CaseRoot, string CaseFolder);
}
