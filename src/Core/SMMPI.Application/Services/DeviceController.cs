using SMMPI.Domain.Interfaces;
using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;

namespace SMMPI.Application.Services;

public class DeviceController : IDeviceController
{
    private readonly IAdbClient _adbClient;
    private readonly IMediaPipeline _mediaPipeline;
    private readonly IDeviceStreamService _streamService;
    private readonly ISessionLogService _sessionLogService;

    public DeviceController(
        IAdbClient adbClient,
        IMediaPipeline mediaPipeline,
        IDeviceStreamService streamService,
        ISessionLogService sessionLogService)
    {
        _adbClient = adbClient;
        _mediaPipeline = mediaPipeline;
        _streamService = streamService;
        _sessionLogService = sessionLogService;
    }

    public AndroidDevice? SelectedDevice { get; private set; }

    public Task EnsureAdbServerAsync(CancellationToken cancellationToken) =>
        _adbClient.EnsureServerAsync(cancellationToken);

    public Task<IReadOnlyList<AndroidDevice>> GetDevicesAsync(CancellationToken cancellationToken) =>
        _adbClient.GetDevicesAsync(cancellationToken);

    public async Task ConnectAsync(AndroidDevice device, CancellationToken cancellationToken)
    {
        SelectedDevice = device;
        await _sessionLogService.LogAsync($"Device selected: {device.DisplayName}", cancellationToken);
    }

    public async Task StartStreamAsync(CancellationToken cancellationToken)
    {
        var device = RequireSelectedDevice();
        await _streamService.StartAsync(device, cancellationToken);
        await _sessionLogService.LogAsync("Device stream started", cancellationToken);
    }

    public async Task StopStreamAsync(CancellationToken cancellationToken)
    {
        await _streamService.StopAsync(cancellationToken);
        await _sessionLogService.LogAsync("Device stream stopped", cancellationToken);
    }

    public async Task<OperationResult> SendMediaAsync(MediaItem media, DeviceProfile profile, CancellationToken cancellationToken)
    {
        var device = RequireSelectedDevice();
        var workingDirectory = Path.Combine(Path.GetTempPath(), "SMMPI", "media");
        Directory.CreateDirectory(workingDirectory);

        var processingResult = await _mediaPipeline.PrepareAsync(
            new MediaProcessingRequest(media, profile, workingDirectory),
            cancellationToken);

        if (!processingResult.Success)
        {
            var message = processingResult.ErrorMessage ?? "Failed to prepare media.";
            await _sessionLogService.LogAsync($"Media preparation failed: {message}", cancellationToken);
            return OperationResult.Fail(message);
        }

        await _adbClient.PushAsync(device.Serial, processingResult.OutputPath, profile.RemoteMediaPath, cancellationToken);
        await _sessionLogService.LogAsync($"Media pushed to device: {profile.OutputFileName}", cancellationToken);
        return OperationResult.Ok($"Sent {profile.OutputFileName} to {device.DisplayName}");
    }

    public Task SendTouchAsync(TouchAction action, int x, int y, CancellationToken cancellationToken)
    {
        var device = RequireSelectedDevice();
        return _adbClient.SendTouchAsync(device.Serial, action, x, y, cancellationToken);
    }

    public Task SendAndroidKeyEventAsync(int androidKeyCode, CancellationToken cancellationToken)
    {
        var device = RequireSelectedDevice();
        return _adbClient.SendKeyEventAsync(device.Serial, androidKeyCode, cancellationToken);
    }

    public Task SendAndroidTextAsync(string text, CancellationToken cancellationToken)
    {
        var device = RequireSelectedDevice();
        return _adbClient.SendTextAsync(device.Serial, text, cancellationToken);
    }

    private AndroidDevice RequireSelectedDevice() =>
        SelectedDevice ?? throw new InvalidOperationException("No device selected.");
}
