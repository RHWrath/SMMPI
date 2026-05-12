namespace SMMPI.Domain.Interfaces;

using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;

public interface IDeviceController
{
    AndroidDevice? SelectedDevice { get; }

    Task EnsureAdbServerAsync(CancellationToken cancellationToken);

    Task<IReadOnlyList<AndroidDevice>> GetDevicesAsync(CancellationToken cancellationToken);

    Task ConnectAsync(AndroidDevice device, CancellationToken cancellationToken);

    Task StartStreamAsync(CancellationToken cancellationToken);

    Task StopStreamAsync(CancellationToken cancellationToken);

    Task<OperationResult> SendMediaAsync(MediaItem media, DeviceProfile profile, CancellationToken cancellationToken);

    Task SendTouchAsync(TouchAction action, int x, int y, CancellationToken cancellationToken);

    Task SendAndroidKeyEventAsync(int androidKeyCode, CancellationToken cancellationToken);

    Task SendAndroidTextAsync(string text, CancellationToken cancellationToken);
}
