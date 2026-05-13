using SMMPI.Domain.Entities;

namespace SMMPI.Domain.Interfaces;

public interface IDeviceStreamService
{
    event EventHandler<StreamFrame>? FrameReceived;

    bool IsRunning { get; }

    Task StartAsync(AndroidDevice device, CancellationToken cancellationToken);

    Task StopAsync(CancellationToken cancellationToken);
}
