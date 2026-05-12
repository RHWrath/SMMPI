using System.Diagnostics;
using System.Text;

namespace SMMPI.Infrastructure.Adb;

public sealed class AdbCommandRunner
{
    public async Task<AdbCommandResult> RunAsync(AdbCommand command, CancellationToken cancellationToken)
    {
        var output = new StringBuilder();
        var error = new StringBuilder();

        var startInfo = new ProcessStartInfo
        {
            FileName = command.FileName,
            Arguments = command.Arguments,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };

        using var process = new Process { StartInfo = startInfo };
        process.OutputDataReceived += (_, e) =>
        {
            if (e.Data is not null)
            {
                output.AppendLine(e.Data);
            }
        };
        process.ErrorDataReceived += (_, e) =>
        {
            if (e.Data is not null)
            {
                error.AppendLine(e.Data);
            }
        };

        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        await process.WaitForExitAsync(cancellationToken);

        return new AdbCommandResult(process.ExitCode, output.ToString(), error.ToString());
    }

    /// <summary>Runs <paramref name="fileName"/> with <paramref name="argumentList"/> (no intermediate shell on Windows — safe for arbitrary <c>input text</c> payloads).</summary>
    public async Task<AdbCommandResult> RunWithArgumentListAsync(string fileName, IReadOnlyList<string> argumentList, CancellationToken cancellationToken)
    {
        var output = new StringBuilder();
        var error = new StringBuilder();

        var startInfo = new ProcessStartInfo
        {
            FileName = fileName,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };

        foreach (var a in argumentList)
        {
            startInfo.ArgumentList.Add(a);
        }

        using var process = new Process { StartInfo = startInfo };
        process.OutputDataReceived += (_, e) =>
        {
            if (e.Data is not null)
            {
                output.AppendLine(e.Data);
            }
        };
        process.ErrorDataReceived += (_, e) =>
        {
            if (e.Data is not null)
            {
                error.AppendLine(e.Data);
            }
        };

        process.Start();
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);

        return new AdbCommandResult(process.ExitCode, output.ToString(), error.ToString());
    }

    public async Task<byte[]> RunBinaryAsync(AdbCommand command, CancellationToken cancellationToken)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = command.FileName,
            Arguments = command.Arguments,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };

        using var process = new Process { StartInfo = startInfo };
        using var memory = new MemoryStream();

        process.Start();
        // Drain stderr concurrently so the child process cannot block if the stderr pipe fills.
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.StandardOutput.BaseStream.CopyToAsync(memory, cancellationToken);
        var stderr = await stderrTask.ConfigureAwait(false);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);

        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException($"ADB binary command failed (exit {process.ExitCode}): {stderr}");
        }

        return memory.ToArray();
    }
}
