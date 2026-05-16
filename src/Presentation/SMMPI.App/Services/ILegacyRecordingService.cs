namespace SMMPI.App.Services;

public interface ILegacyRecordingService : IAsyncDisposable
{
    Task StartSessionAsync(string officerName, string caseNumber, string caseRoot, CancellationToken cancellationToken);

    Task StartRecordingAsync(string platformName, int x, int y, int width, int height, string windowTitle, CancellationToken cancellationToken);

    Task<string?> StopRecordingAsync(CancellationToken cancellationToken);

    Task UpdateRecordingCropAsync(int x, int y, int width, int height, CancellationToken cancellationToken);
}
