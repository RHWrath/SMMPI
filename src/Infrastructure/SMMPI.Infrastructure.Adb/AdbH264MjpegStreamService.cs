using System.Diagnostics;
using System.Runtime.InteropServices;
using SMMPI.Domain.Entities;
using SMMPI.Domain.Interfaces;

namespace SMMPI.Infrastructure.Adb;

/// <summary>
/// Low-latency preview: <c>adb exec-out screenrecord</c> (H.264) → FFmpeg → MJPEG over a pipe, then JPEG frames to the UI.
/// Does not use <see cref="AdbService"/>'s global ADB lock for the long-running pipe (only <see cref="IAdbClient.EnsureServerAsync"/> at chunk start).
/// </summary>
public sealed class AdbH264MjpegStreamService : IDeviceStreamService, IStreamTouchInteractionPause
{
    private readonly IAdbClient _adbClient;
    private readonly string _ffmpegPath;
    private readonly int _screenrecordChunkSeconds;
    private CancellationTokenSource? _streamCancellation;
    private Task? _streamTask;

    public AdbH264MjpegStreamService(IAdbClient adbClient, string? ffmpegExecutable = null, int screenrecordChunkSeconds = 180)
    {
        _adbClient = adbClient;
        _ffmpegPath = string.IsNullOrWhiteSpace(ffmpegExecutable) ? FfmpegLocator.Resolve() : ffmpegExecutable.Trim();
        _screenrecordChunkSeconds = Math.Clamp(screenrecordChunkSeconds, 10, 600);
    }

    public event EventHandler<StreamFrame>? FrameReceived;

    public bool IsRunning { get; private set; }

    /// <inheritdoc />
    public void PushInteractionPause()
    {
        // H.264 pipe is not paused here (would require draining the pipe without blocking touch). PNG screencap path pauses instead.
    }

    /// <inheritdoc />
    public void PopInteractionPause()
    {
    }

    public Task StartAsync(AndroidDevice device, CancellationToken cancellationToken)
    {
        if (IsRunning)
        {
            return Task.CompletedTask;
        }

        _streamCancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        IsRunning = true;
        var serial = device.Serial;
        _streamTask = Task.Run(() => CaptureLoopAsync(serial, _streamCancellation.Token), CancellationToken.None);
        return Task.CompletedTask;
    }

    public async Task StopAsync(CancellationToken cancellationToken)
    {
        if (!IsRunning)
        {
            return;
        }

        IsRunning = false;
        _streamCancellation?.Cancel();

        if (_streamTask is not null)
        {
            try
            {
                await _streamTask.WaitAsync(cancellationToken).ConfigureAwait(false);
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
            try
            {
                await _adbClient.EnsureServerAsync(cancellationToken).ConfigureAwait(false);
                await RunOneScreenrecordChunkAsync(serial, cancellationToken).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch
            {
                try
                {
                    await Task.Delay(300, cancellationToken).ConfigureAwait(false);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }
        }
    }

    private async Task RunOneScreenrecordChunkAsync(string serial, CancellationToken cancellationToken)
    {
        using var adb = new Process();
        adb.StartInfo.FileName = AdbLocator.Resolve();
        adb.StartInfo.UseShellExecute = false;
        adb.StartInfo.RedirectStandardOutput = true;
        adb.StartInfo.RedirectStandardError = true;
        adb.StartInfo.CreateNoWindow = true;
        adb.StartInfo.ArgumentList.Add("-s");
        adb.StartInfo.ArgumentList.Add(serial);
        adb.StartInfo.ArgumentList.Add("exec-out");
        adb.StartInfo.ArgumentList.Add("screenrecord");
        adb.StartInfo.ArgumentList.Add("--output-format");
        adb.StartInfo.ArgumentList.Add("h264");
        adb.StartInfo.ArgumentList.Add("--bit-rate");
        adb.StartInfo.ArgumentList.Add("12000000");
        adb.StartInfo.ArgumentList.Add("--time-limit");
        adb.StartInfo.ArgumentList.Add(_screenrecordChunkSeconds.ToString(System.Globalization.CultureInfo.InvariantCulture));
        adb.StartInfo.ArgumentList.Add("-");

        using var ffmpeg = new Process();
        ffmpeg.StartInfo.FileName = _ffmpegPath;
        ffmpeg.StartInfo.UseShellExecute = false;
        ffmpeg.StartInfo.RedirectStandardInput = true;
        ffmpeg.StartInfo.RedirectStandardOutput = true;
        ffmpeg.StartInfo.RedirectStandardError = true;
        ffmpeg.StartInfo.CreateNoWindow = true;
        ffmpeg.StartInfo.ArgumentList.Add("-hide_banner");
        ffmpeg.StartInfo.ArgumentList.Add("-loglevel");
        ffmpeg.StartInfo.ArgumentList.Add("error");
        ffmpeg.StartInfo.ArgumentList.Add("-fflags");
        ffmpeg.StartInfo.ArgumentList.Add("+genpts+discardcorrupt");
        ffmpeg.StartInfo.ArgumentList.Add("-probesize");
        ffmpeg.StartInfo.ArgumentList.Add("32768");
        ffmpeg.StartInfo.ArgumentList.Add("-analyzeduration");
        ffmpeg.StartInfo.ArgumentList.Add("0");
        ffmpeg.StartInfo.ArgumentList.Add("-f");
        ffmpeg.StartInfo.ArgumentList.Add("h264");
        ffmpeg.StartInfo.ArgumentList.Add("-i");
        ffmpeg.StartInfo.ArgumentList.Add("-");
        ffmpeg.StartInfo.ArgumentList.Add("-an");
        ffmpeg.StartInfo.ArgumentList.Add("-vf");
        ffmpeg.StartInfo.ArgumentList.Add("fps=30,scale=1280:-2");
        ffmpeg.StartInfo.ArgumentList.Add("-f");
        ffmpeg.StartInfo.ArgumentList.Add("image2pipe");
        ffmpeg.StartInfo.ArgumentList.Add("-vcodec");
        ffmpeg.StartInfo.ArgumentList.Add("mjpeg");
        ffmpeg.StartInfo.ArgumentList.Add("-q:v");
        ffmpeg.StartInfo.ArgumentList.Add("4");
        ffmpeg.StartInfo.ArgumentList.Add("-");

        adb.Start();
        ffmpeg.Start();

        // If stderr is redirected but never read, the adb pipe can fill and block screenrecord entirely.
        var adbStderrDrain = adb.StandardError.ReadToEndAsync(cancellationToken);
        var stderrDrain = ffmpeg.StandardError.ReadToEndAsync(cancellationToken);
        Task copyTask;
        try
        {
            copyTask = adb.StandardOutput.BaseStream.CopyToAsync(ffmpeg.StandardInput.BaseStream, cancellationToken);
        }
        catch
        {
            TryKill(adb);
            TryKill(ffmpeg);
            throw;
        }

        var accumulator = new JpegPipeAccumulator();
        var buffer = new byte[64 * 1024];
        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                var read = await ffmpeg.StandardOutput.BaseStream.ReadAsync(buffer.AsMemory(0, buffer.Length), cancellationToken).ConfigureAwait(false);
                if (read == 0)
                {
                    break;
                }

                accumulator.Append(buffer.AsSpan(0, read));
                while (accumulator.TryExtractFrame(out var jpeg))
                {
                    var (w, h) = JpegSizeReader.Read(jpeg);
                    if (w <= 0 || h <= 0)
                    {
                        continue;
                    }

                    FrameReceived?.Invoke(this, new StreamFrame(jpeg, w, h, DateTimeOffset.UtcNow, StreamFrameFormat.Jpeg));
                }
            }
        }
        finally
        {
            try
            {
                ffmpeg.StandardInput.Close();
            }
            catch
            {
            }

            try
            {
                await copyTask.ConfigureAwait(false);
            }
            catch
            {
            }

            TryKill(adb);
            TryKill(ffmpeg);
            adb.WaitForExit(2000);
            ffmpeg.WaitForExit(2000);
            try
            {
                _ = await adbStderrDrain.ConfigureAwait(false);
            }
            catch
            {
            }

            try
            {
                _ = await stderrDrain.ConfigureAwait(false);
            }
            catch
            {
            }
        }
    }

    private static void TryKill(Process p)
    {
        try
        {
            if (!p.HasExited)
            {
                p.Kill(entireProcessTree: true);
            }
        }
        catch
        {
        }
    }

    private sealed class JpegPipeAccumulator
    {
        private const int MaxBufferBytes = 10 * 1024 * 1024;
        private readonly List<byte> _data = new(1 << 16);

        public void Append(ReadOnlySpan<byte> span)
        {
            if (_data.Count + span.Length > MaxBufferBytes)
            {
                _data.Clear();
            }

            _data.AddRange(span);
        }

        public bool TryExtractFrame(out byte[] jpeg)
        {
            var span = CollectionsMarshal.AsSpan(_data);
            var soi = FindMarkerPair(span, 0xFF, 0xD8);
            if (soi < 0)
            {
                if (_data.Count > MaxBufferBytes / 2)
                {
                    _data.Clear();
                }

                jpeg = Array.Empty<byte>();
                return false;
            }

            if (soi > 0)
            {
                _data.RemoveRange(0, soi);
                span = CollectionsMarshal.AsSpan(_data);
            }

            var eoi = FindMarkerPair(span, 0xFF, 0xD9, startOffset: 2);
            if (eoi < 0)
            {
                jpeg = Array.Empty<byte>();
                return false;
            }

            var len = eoi + 2;
            if (len < 64)
            {
                _data.RemoveRange(0, Math.Min(len, _data.Count));
                jpeg = Array.Empty<byte>();
                return false;
            }

            jpeg = span[..len].ToArray();
            _data.RemoveRange(0, len);
            return true;
        }

        private static int FindMarkerPair(ReadOnlySpan<byte> span, byte a, byte b, int startOffset = 0)
        {
            for (var i = startOffset; i < span.Length - 1; i++)
            {
                if (span[i] == a && span[i + 1] == b)
                {
                    return i;
                }
            }

            return -1;
        }
    }
}
