namespace SMMPI.Domain.Interfaces;

public interface IStreamRecordingService : IAsyncDisposable
{
    bool IsRecording { get; }

    Task StartSessionAsync(string officerName, string caseNumber, string caseRoot, CancellationToken cancellationToken);

    Task StartRecordingAsync(string platformName, CancellationToken cancellationToken);

    Task<string?> StopRecordingAsync(CancellationToken cancellationToken);
}
