namespace SMMPI.Infrastructure.Adb;

public sealed record AdbCommandResult(int ExitCode, string StandardOutput, string StandardError)
{
    public bool Success => ExitCode == 0;
}
