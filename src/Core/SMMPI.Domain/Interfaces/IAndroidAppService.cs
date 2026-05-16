namespace SMMPI.Domain.Interfaces;

public interface IAndroidAppService
{
    Task TriggerMediaScanAsync(string serial, string remotePath, CancellationToken cancellationToken);

    Task ForceStopAsync(string serial, string packageName, CancellationToken cancellationToken);

    Task ForceStopAndRelaunchAsync(string serial, string packageName, CancellationToken cancellationToken);
}
