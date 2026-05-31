using SMMPI.Domain.Entities;

namespace SMMPI.Domain.Interfaces;

public interface IAndroidStreamingService : IAsyncDisposable
{
    event EventHandler<AndroidStreamingState>? StateChanged;

    AndroidStreamingState State { get; }

    Task<OperationResult> StartAsync(AndroidDevice device, AndroidStreamingOptions options, CancellationToken cancellationToken);

    Task StopAsync(CancellationToken cancellationToken);
}
