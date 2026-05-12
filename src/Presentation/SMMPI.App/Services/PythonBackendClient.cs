using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace WPFTest.Services;

/// <summary>
/// Owns the local Python backend process and the two socket connections used by the WPF frontend.
/// </summary>
public sealed class PythonBackendClient : IAsyncDisposable
{
    private readonly ConcurrentDictionary<int, TaskCompletionSource<JsonElement>> _pending = new();
    private readonly CancellationTokenSource _shutdown = new();
    private Process? _process;
    private TcpClient? _controlClient;
    private TcpClient? _frameClient;
    private StreamWriter? _controlWriter;
    private int _nextId;

    public event EventHandler<JsonElement>? EventReceived;
    public event EventHandler<PythonStreamFrame>? FrameReceived;
    public event EventHandler<string>? LogReceived;

    /// <summary>
    /// Starts the Python backend, reads its advertised ports, and connects the control and frame sockets.
    /// </summary>
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        if (_process is not null)
        {
            return;
        }

        var backendPath = ResolveBackendPath();
        var backendDir = Path.GetDirectoryName(backendPath)!;
        var python = await ResolvePythonAsync(backendDir, cancellationToken).ConfigureAwait(false);

        var startInfo = new ProcessStartInfo
        {
            FileName = python,
            WorkingDirectory = backendDir,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };
        startInfo.ArgumentList.Add(backendPath);
        startInfo.ArgumentList.Add("--control-port");
        startInfo.ArgumentList.Add("0");
        startInfo.ArgumentList.Add("--frame-port");
        startInfo.ArgumentList.Add("0");

        _process = Process.Start(startInfo) ?? throw new InvalidOperationException("Python backend could not be started.");
        _ = Task.Run(() => DrainLogsAsync(_process.StandardError, _shutdown.Token), CancellationToken.None);

        var readyLine = await _process.StandardOutput.ReadLineAsync(cancellationToken).ConfigureAwait(false);
        if (string.IsNullOrWhiteSpace(readyLine))
        {
            throw new InvalidOperationException("Python backend did not report its ports.");
        }

        using var ready = JsonDocument.Parse(readyLine);
        var controlPort = ready.RootElement.GetProperty("control_port").GetInt32();
        var framePort = ready.RootElement.GetProperty("frame_port").GetInt32();
        _ = Task.Run(() => DrainLogsAsync(_process.StandardOutput, _shutdown.Token), CancellationToken.None);

        _controlClient = new TcpClient();
        await _controlClient.ConnectAsync("127.0.0.1", controlPort, cancellationToken).ConfigureAwait(false);
        _controlWriter = new StreamWriter(_controlClient.GetStream(), new UTF8Encoding(false)) { AutoFlush = true };

        _frameClient = new TcpClient();
        await _frameClient.ConnectAsync("127.0.0.1", framePort, cancellationToken).ConfigureAwait(false);

        _ = Task.Run(() => ReadControlLoopAsync(_controlClient, _shutdown.Token), CancellationToken.None);
        _ = Task.Run(() => ReadFrameLoopAsync(_frameClient, _shutdown.Token), CancellationToken.None);
    }

    /// <summary>
    /// Sends a JSON command to the backend and awaits the matching response by request id.
    /// </summary>
    public async Task<JsonElement> SendAsync(string command, object? args = null, CancellationToken cancellationToken = default)
    {
        if (_controlWriter is null)
        {
            throw new InvalidOperationException("Python backend is not connected.");
        }

        var id = Interlocked.Increment(ref _nextId);
        var tcs = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        if (!_pending.TryAdd(id, tcs))
        {
            throw new InvalidOperationException("Could not register backend request.");
        }

        var payload = JsonSerializer.Serialize(new
        {
            id,
            command,
            args = args ?? new { },
        });

        await _controlWriter.WriteLineAsync(payload.AsMemory(), cancellationToken).ConfigureAwait(false);

        await using var registration = cancellationToken.Register(() => tcs.TrySetCanceled(cancellationToken));
        var response = await tcs.Task.ConfigureAwait(false);
        if (response.TryGetProperty("ok", out var ok) && !ok.GetBoolean())
        {
            var error = response.TryGetProperty("error", out var err) ? err.GetString() : "Python backend command failed.";
            throw new InvalidOperationException(error);
        }

        return response;
    }

    /// <summary>
    /// Reads backend control messages and routes responses to pending commands or raises backend events.
    /// </summary>
    private async Task ReadControlLoopAsync(TcpClient client, CancellationToken cancellationToken)
    {
        try
        {
            using var reader = new StreamReader(client.GetStream(), Encoding.UTF8);
            while (!cancellationToken.IsCancellationRequested)
            {
                var line = await reader.ReadLineAsync(cancellationToken).ConfigureAwait(false);
                if (line is null)
                {
                    break;
                }

                using var doc = JsonDocument.Parse(line);
                var root = doc.RootElement.Clone();
                var type = root.TryGetProperty("type", out var typeProp) ? typeProp.GetString() : null;
                if (type == "response" && root.TryGetProperty("id", out var idProp))
                {
                    if (_pending.TryRemove(idProp.GetInt32(), out var tcs))
                    {
                        tcs.TrySetResult(root);
                    }
                }
                else if (type == "event")
                {
                    EventReceived?.Invoke(this, root);
                }
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception ex)
        {
            LogReceived?.Invoke(this, $"Backend control connection closed: {ex.Message}");
        }
    }

    /// <summary>
    /// Reads length-prefixed frame packets from Python and raises decoded frame events for the UI.
    /// </summary>
    private async Task ReadFrameLoopAsync(TcpClient client, CancellationToken cancellationToken)
    {
        var stream = client.GetStream();
        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                var metaLength = await ReadInt32Async(stream, cancellationToken).ConfigureAwait(false);
                var metaBytes = await ReadExactAsync(stream, metaLength, cancellationToken).ConfigureAwait(false);
                var payloadLength = await ReadInt32Async(stream, cancellationToken).ConfigureAwait(false);
                var payload = await ReadExactAsync(stream, payloadLength, cancellationToken).ConfigureAwait(false);

                using var metaDoc = JsonDocument.Parse(metaBytes);
                var meta = metaDoc.RootElement;
                FrameReceived?.Invoke(
                    this,
                    new PythonStreamFrame(
                        payload,
                        meta.GetProperty("width").GetInt32(),
                        meta.GetProperty("height").GetInt32(),
                        meta.TryGetProperty("format", out var fmt) ? fmt.GetString() ?? "jpeg" : "jpeg"));
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception ex)
        {
            LogReceived?.Invoke(this, $"Backend frame connection closed: {ex.Message}");
        }
    }

    /// <summary>
    /// Reads a big-endian 32-bit integer from the stream.
    /// </summary>
    private static async Task<int> ReadInt32Async(Stream stream, CancellationToken cancellationToken)
    {
        var bytes = await ReadExactAsync(stream, 4, cancellationToken).ConfigureAwait(false);
        return (bytes[0] << 24) | (bytes[1] << 16) | (bytes[2] << 8) | bytes[3];
    }

    /// <summary>
    /// Reads exactly the requested number of bytes or fails if the socket closes early.
    /// </summary>
    private static async Task<byte[]> ReadExactAsync(Stream stream, int length, CancellationToken cancellationToken)
    {
        var buffer = new byte[length];
        var offset = 0;
        while (offset < length)
        {
            var read = await stream.ReadAsync(buffer.AsMemory(offset, length - offset), cancellationToken).ConfigureAwait(false);
            if (read == 0)
            {
                throw new EndOfStreamException();
            }

            offset += read;
        }

        return buffer;
    }

    /// <summary>
    /// Forwards backend stdout or stderr lines to the WPF status/log event stream.
    /// </summary>
    private async Task DrainLogsAsync(StreamReader reader, CancellationToken cancellationToken)
    {
        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                var line = await reader.ReadLineAsync(cancellationToken).ConfigureAwait(false);
                if (line is null)
                {
                    return;
                }

                LogReceived?.Invoke(this, line);
            }
        }
        catch (OperationCanceledException)
        {
        }
    }

    /// <summary>
    /// Finds the Python backend entrypoint by walking upward from the app output directory.
    /// </summary>
    private static string ResolveBackendPath()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "packages", "Prototype", "backend_server.py");
            if (File.Exists(candidate))
            {
                return candidate;
            }

            dir = dir.Parent;
        }

        throw new FileNotFoundException("Could not find packages\\Prototype\\backend_server.py from the application directory.");
    }

    /// <summary>
    /// Resolves the Python executable, creating and refreshing the prototype virtual environment when needed.
    /// </summary>
    private static async Task<string> ResolvePythonAsync(string backendDir, CancellationToken cancellationToken)
    {
        var explicitPython = Environment.GetEnvironmentVariable("SMMPI_PYTHON");
        if (!string.IsNullOrWhiteSpace(explicitPython))
        {
            return explicitPython;
        }

        var venvPython = Path.Combine(backendDir, ".venv", "Scripts", "python.exe");
        if (!File.Exists(venvPython))
        {
            await RunProcessAsync("python", "-m venv .venv", backendDir, cancellationToken).ConfigureAwait(false);
        }

        var requirements = Path.Combine(backendDir, "requirements.txt");
        var marker = Path.Combine(backendDir, ".wpf_backend_requirements_installed");
        if (File.Exists(requirements) && (!File.Exists(marker) || File.GetLastWriteTimeUtc(marker) < File.GetLastWriteTimeUtc(requirements)))
        {
            await RunProcessAsync(venvPython, "-m pip install -r requirements.txt", backendDir, cancellationToken).ConfigureAwait(false);
            File.WriteAllText(marker, DateTimeOffset.UtcNow.ToString("O"));
        }

        return venvPython;
    }

    /// <summary>
    /// Runs a setup process and throws with captured output if it exits unsuccessfully.
    /// </summary>
    private static async Task RunProcessAsync(string fileName, string arguments, string workingDirectory, CancellationToken cancellationToken)
    {
        using var process = Process.Start(new ProcessStartInfo
        {
            FileName = fileName,
            Arguments = arguments,
            WorkingDirectory = workingDirectory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        }) ?? throw new InvalidOperationException($"Could not start process: {fileName}");

        var stdout = await process.StandardOutput.ReadToEndAsync(cancellationToken).ConfigureAwait(false);
        var stderr = await process.StandardError.ReadToEndAsync(cancellationToken).ConfigureAwait(false);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException($"{fileName} {arguments} failed.{Environment.NewLine}{stderr}{stdout}");
        }
    }

    /// <summary>
    /// Requests backend shutdown, closes sockets, and kills the process if it is still running.
    /// </summary>
    public async ValueTask DisposeAsync()
    {
        if (_controlWriter is not null)
        {
            try
            {
                await SendAsync("shutdown", cancellationToken: CancellationToken.None).ConfigureAwait(false);
            }
            catch
            {
            }
        }

        _shutdown.Cancel();
        _controlWriter?.Dispose();
        _controlClient?.Dispose();
        _frameClient?.Dispose();
        if (_process is { HasExited: false })
        {
            try
            {
                _process.Kill(entireProcessTree: true);
            }
            catch
            {
            }
        }

        _process?.Dispose();
        _shutdown.Dispose();
    }
}

/// <summary>
/// Represents one image frame received from the Python stream socket.
/// </summary>
public sealed record PythonStreamFrame(byte[] ImageBytes, int Width, int Height, string Format);
