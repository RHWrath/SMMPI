using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Adb;

public sealed class AndroidAppService : IAndroidAppService
{
    private readonly IAdbClient _adbClient;

    public AndroidAppService(IAdbClient adbClient)
    {
        _adbClient = adbClient;
    }

    public Task TriggerMediaScanAsync(string serial, string remotePath, CancellationToken cancellationToken) =>
        _adbClient.ShellAsync(serial, $"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{remotePath}", cancellationToken);

    public Task ForceStopAsync(string serial, string packageName, CancellationToken cancellationToken) =>
        _adbClient.ShellAsync(serial, $"am force-stop {packageName}", cancellationToken);

    public async Task ForceStopAndRelaunchAsync(string serial, string packageName, CancellationToken cancellationToken)
    {
        await ForceStopAsync(serial, packageName, cancellationToken).ConfigureAwait(false);
        await _adbClient.ShellAsync(
            serial,
            $"monkey -p {packageName} -c android.intent.category.LAUNCHER 1",
            cancellationToken).ConfigureAwait(false);
    }
}
