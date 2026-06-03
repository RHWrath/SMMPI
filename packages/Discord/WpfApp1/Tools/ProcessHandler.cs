using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;

namespace SMMPI.Infrastructure.Plugins.Tools
{
    public class ProcessHandler
    {
        public static async Task<bool> TryRunProcessAsync(string fileName, string arguments, string workingDir)
        {
            try
            {
                await RunProcessCheckedAsync(fileName, arguments, workingDir);
                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Check failed: {fileName} {arguments}");
                Console.WriteLine(ex.Message);
                return false;
            }
        }

        public static async Task RunProcessCheckedAsync(string fileName, string arguments, string workingDir, Action<string>? onOutput = null)
        {
            var output = new StringBuilder();
            var error = new StringBuilder();

            var psi = new ProcessStartInfo
            {
                FileName = fileName,
                Arguments = arguments,
                WorkingDirectory = workingDir,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };

            using (var process = new Process())
            {
                process.StartInfo = psi;

                process.OutputDataReceived += (_, e) =>
                {
                    if (e.Data is null) return;
                    output.AppendLine(e.Data);
                    Console.WriteLine("[out] " + e.Data);
                    onOutput?.Invoke("[out] " + e.Data);
                };

                process.ErrorDataReceived += (_, e) =>
                {
                    if (e.Data is null) return;
                    error.AppendLine(e.Data);
                    Console.WriteLine("[err] " + e.Data);
                    onOutput?.Invoke("[err] " + e.Data);
                };

                process.Start();

                process.BeginOutputReadLine();
                process.BeginErrorReadLine();

                await process.WaitForExitAsync();

                if (process.ExitCode != 0)
                {
                    throw new InvalidOperationException(
                        $"Process failed with exit code {process.ExitCode}\n" +
                        $"Command: {fileName} {arguments}\n\n" +
                        $"STDOUT:\n{output}\n" +
                        $"STDERR:\n{error}");
                }
            }
        }
    }
}
