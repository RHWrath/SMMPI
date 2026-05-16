namespace SMMPI.App.Services;

public sealed class LegacyPythonRecordingService : ILegacyRecordingService
{
    private readonly PythonBackendClient _backend;
    private bool _started;
    private bool _sessionStarted;
    private (string OfficerName, string CaseNumber, string CaseRoot)? _session;

    public LegacyPythonRecordingService(PythonBackendClient backend)
    {
        _backend = backend;
    }

    public Task StartSessionAsync(string officerName, string caseNumber, string caseRoot, CancellationToken cancellationToken)
    {
        _session = (officerName, caseNumber, caseRoot);
        return Task.CompletedTask;
    }

    public async Task StartRecordingAsync(string platformName, int x, int y, int width, int height, string windowTitle, CancellationToken cancellationToken)
    {
        await EnsureStartedAsync(cancellationToken).ConfigureAwait(false);
        await EnsureSessionStartedAsync(cancellationToken).ConfigureAwait(false);
        await _backend.SendAsync(
            "start_recording",
            new
            {
                x,
                y,
                width,
                height,
                windowTitle,
                platformName,
            },
            cancellationToken).ConfigureAwait(false);
    }

    public async Task<string?> StopRecordingAsync(CancellationToken cancellationToken)
    {
        var response = await _backend.SendAsync("stop_recording", cancellationToken: cancellationToken).ConfigureAwait(false);
        return response.TryGetProperty("path", out var path) ? path.GetString() : null;
    }

    public Task UpdateRecordingCropAsync(int x, int y, int width, int height, CancellationToken cancellationToken) =>
        _backend.SendAsync(
            "update_recording_crop",
            new { x, y, width, height },
            cancellationToken);

    public ValueTask DisposeAsync() => _backend.DisposeAsync();

    private async Task EnsureStartedAsync(CancellationToken cancellationToken)
    {
        if (_started)
        {
            return;
        }

        await _backend.StartAsync(cancellationToken).ConfigureAwait(false);
        _started = true;
    }

    private async Task EnsureSessionStartedAsync(CancellationToken cancellationToken)
    {
        if (_sessionStarted)
        {
            return;
        }

        var session = _session ?? throw new InvalidOperationException("No recording session has been configured.");
        await _backend.SendAsync(
            "start_session",
            new
            {
                officerName = session.OfficerName,
                caseNumber = session.CaseNumber,
                caseRoot = session.CaseRoot,
            },
            cancellationToken).ConfigureAwait(false);
        _sessionStarted = true;
    }
}
