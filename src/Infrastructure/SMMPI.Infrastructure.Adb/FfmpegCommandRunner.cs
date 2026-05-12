using System.Diagnostics;
using System.Text;

namespace SMMPI.Infrastructure.Adb;

public sealed class FfmpegCommandRunner
{
    public async Task<string> RunAsync(FfmpegCommand command, CancellationToken cancellationToken)
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

        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException($"FFmpeg command failed: {error}");
        }

        return output.ToString().Trim();
    }
}
