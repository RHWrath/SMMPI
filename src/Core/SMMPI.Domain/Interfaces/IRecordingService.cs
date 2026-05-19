using SMMPI.Domain.Entities;

namespace SMMPI.Domain.Interfaces;

public interface IRecordingService : IAsyncDisposable
{
    bool IsRecording { get; }

    Task StartSessionAsync(string officerName, string caseNumber, string caseRoot, CancellationToken cancellationToken);

    Task<OperationResult> StartRecordingAsync(AndroidDevice device, string platformName, bool audioEnabled, CancellationToken cancellationToken);

    Task<RecordingResult?> StopRecordingAsync(CancellationToken cancellationToken);
}
