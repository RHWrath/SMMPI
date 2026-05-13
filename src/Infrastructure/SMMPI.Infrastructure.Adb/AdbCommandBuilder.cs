using SMMPI.Domain.Enums;

namespace SMMPI.Infrastructure.Adb;

public sealed class AdbCommandBuilder
{
    private readonly string _adbExecutable;

    /// <param name="adbExecutable">Absolute path to adb, or <c>null</c> to resolve via <see cref="AdbLocator"/>.</param>
    public AdbCommandBuilder(string? adbExecutable = null)
    {
        _adbExecutable = string.IsNullOrWhiteSpace(adbExecutable)
            ? AdbLocator.Resolve()
            : adbExecutable.Trim();
    }

    /// <summary>Resolved <c>adb</c> executable path (for argv-based invocations).</summary>
    public string AdbExecutable => _adbExecutable;

    public AdbCommand BuildStartServer() => new(_adbExecutable, "start-server");

    public AdbCommand BuildDevices() => new(_adbExecutable, "devices -l");

    public AdbCommand BuildShell(string serial, params string[] commandParts) =>
        new(_adbExecutable, $"-s {QuoteIfNeeded(serial)} shell {string.Join(' ', commandParts)}");

    public AdbCommand BuildPush(string serial, string localPath, string remotePath) =>
        new(_adbExecutable, $"-s {QuoteIfNeeded(serial)} push {Quote(localPath)} {Quote(remotePath)}");

    public AdbCommand BuildTouch(string serial, TouchAction action, int x, int y) =>
        BuildShell(serial, "input", "motionevent", ToAdbTouchAction(action), x.ToString(), y.ToString());

    /// <summary>
    /// Raw PNG bytes on stdout. Prefer <c>exec-out</c> over <c>shell</c> on Windows so line-ending translation does not corrupt PNG data.
    /// </summary>
    public AdbCommand BuildScreencap(string serial) =>
        new(_adbExecutable, $"-s {QuoteIfNeeded(serial)} exec-out screencap -p");

    private static string ToAdbTouchAction(TouchAction action) => action switch
    {
        TouchAction.Down => "DOWN",
        TouchAction.Move => "MOVE",
        TouchAction.Up => "UP",
        _ => throw new ArgumentOutOfRangeException(nameof(action), action, "Unsupported touch action.")
    };

    private static string QuoteIfNeeded(string value)
    {
        if (value.StartsWith('"') && value.EndsWith('"'))
        {
            return value;
        }

        return value.Any(char.IsWhiteSpace) ? $"\"{value}\"" : value;
    }

    private static string Quote(string value) =>
        value.StartsWith('"') && value.EndsWith('"') ? value : $"\"{value}\"";
}
