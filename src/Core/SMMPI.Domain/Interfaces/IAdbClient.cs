using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;

namespace SMMPI.Domain.Interfaces;

public interface IAdbClient
{
    Task EnsureServerAsync(CancellationToken cancellationToken);

    Task<IReadOnlyList<AndroidDevice>> GetDevicesAsync(CancellationToken cancellationToken);

    Task<string> ShellAsync(string serial, string command, CancellationToken cancellationToken);

    Task PushAsync(string serial, string localPath, string remotePath, CancellationToken cancellationToken);

    Task SendTouchAsync(string serial, TouchAction action, int x, int y, CancellationToken cancellationToken);

    /// <summary>Sends an Android <c>KeyEvent</c> keycode via <c>adb shell input keyevent</c>.</summary>
    Task SendKeyEventAsync(string serial, int androidKeyCode, CancellationToken cancellationToken);

    /// <summary>Sends UTF-16 text via <c>adb shell input text</c> (chunked).</summary>
    Task SendTextAsync(string serial, string text, CancellationToken cancellationToken);

    Task<byte[]> CaptureScreenAsync(string serial, CancellationToken cancellationToken);
}
