using System.Diagnostics;
using SMMPI.Domain.Entities;
using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Adb;

public sealed class AdbScreencapStreamService : IDeviceStreamService, IStreamTouchInteractionPause
{
    private readonly IAdbClient _adbClient;
    /// <summary>Minimum time between starting consecutive captures (USB + PNG is slow; lower = snappier but more CPU/USB load).</summary>
    private readonly int _minimumIntervalMs;
    private int _interactionPause;
    private int _consecutiveCaptureErrors;
    private CancellationTokenSource? _streamCancellation;
    private Task? _streamTask;

    public AdbScreencapStreamService(IAdbClient adbClient, int minimumIntervalMsBetweenCaptures = 40)
    {
        _adbClient = adbClient;
        _minimumIntervalMs = Math.Clamp(minimumIntervalMsBetweenCaptures, 16, 500);
    }

    public event EventHandler<StreamFrame>? FrameReceived;

    public bool IsRunning { get; private set; }

    /// <summary>Pause PNG capture while the operator drags on the preview so touch commands are not queued behind large <c>screencap</c> transfers.</summary>
    public void PushInteractionPause() => Interlocked.Increment(ref _interactionPause);

    public void PopInteractionPause()
    {
        while (true)
        {
            var cur = Volatile.Read(ref _interactionPause);
            var next = Math.Max(0, cur - 1);
            if (Interlocked.CompareExchange(ref _interactionPause, next, cur) == cur)
            {
                return;
            }
        }
    }

    public Task StartAsync(AndroidDevice device, CancellationToken cancellationToken)
    {
        if (IsRunning)
        {
            return Task.CompletedTask;
        }

        _streamCancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        IsRunning = true;
        _streamTask = Task.Run(() => CaptureLoopAsync(device.Serial, _streamCancellation.Token), CancellationToken.None);
        return Task.CompletedTask;
    }

    public async Task StopAsync(CancellationToken cancellationToken)
    {
        if (!IsRunning)
        {
            return;
        }

        IsRunning = false;
        Interlocked.Exchange(ref _interactionPause, 0);
        _streamCancellation?.Cancel();

        if (_streamTask is not null)
        {
            try
            {
                await _streamTask.WaitAsync(cancellationToken);
            }
            catch (OperationCanceledException)
            {
            }
        }

        _streamCancellation?.Dispose();
        _streamCancellation = null;
        _streamTask = null;
    }

    private async Task CaptureLoopAsync(string serial, CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested)
        {
            if (Volatile.Read(ref _interactionPause) > 0)
            {
                try
                {
                    await Task.Delay(8, cancellationToken).ConfigureAwait(false);
                }
                catch (OperationCanceledException)
                {
                    break;
                }

                continue;
            }

            var iterationStart = Stopwatch.GetTimestamp();
            try
            {
                var bytes = await _adbClient.CaptureScreenAsync(serial, cancellationToken).ConfigureAwait(false);
                var size = PngSizeReader.Read(bytes);
                FrameReceived?.Invoke(this, new StreamFrame(bytes, size.Width, size.Height, DateTimeOffset.UtcNow, StreamFrameFormat.Png));
                Interlocked.Exchange(ref _consecutiveCaptureErrors, 0);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch
            {
                var n = Interlocked.Increment(ref _consecutiveCaptureErrors);
                // Short retries first so a single bad frame does not freeze the preview for a full second.
                var delayMs = Math.Min(1200, 40 * (1 << Math.Min(n - 1, 5)));
                try
                {
                    await Task.Delay(delayMs, cancellationToken).ConfigureAwait(false);
                }
                catch (OperationCanceledException)
                {
                    break;
                }

                continue;
            }

            var elapsedMs = Stopwatch.GetElapsedTime(iterationStart).TotalMilliseconds;
            var waitMs = _minimumIntervalMs - elapsedMs;
            if (waitMs > 0)
            {
                try
                {
                    await Task.Delay(TimeSpan.FromMilliseconds(waitMs), cancellationToken).ConfigureAwait(false);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }
        }
    }
}
