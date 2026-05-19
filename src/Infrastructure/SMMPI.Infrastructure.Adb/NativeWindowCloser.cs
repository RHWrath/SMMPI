using System.Runtime.InteropServices;
using System.Text;

namespace SMMPI.Infrastructure.Adb;

internal static class NativeWindowCloser
{
    private const int WmClose = 0x0010;

    public static int CloseWindowsForProcess(int processId, string? windowTitle)
    {
        var closed = 0;
        foreach (var hwnd in FindWindows(processId, windowTitle))
        {
            if (PostMessage(hwnd, WmClose, nint.Zero, nint.Zero))
            {
                closed++;
            }
        }

        return closed;
    }

    private static IReadOnlyList<nint> FindWindows(int processId, string? windowTitle)
    {
        var result = new List<nint>();
        EnumWindows(
            (hwnd, _) =>
            {
                AddIfMatch(hwnd, processId, windowTitle, result);
                EnumChildWindows(
                    hwnd,
                    (child, _) =>
                    {
                        AddIfMatch(child, processId, windowTitle, result);
                        return true;
                    },
                    nint.Zero);
                return true;
            },
            nint.Zero);
        return result.Distinct().ToArray();
    }

    private static void AddIfMatch(nint hwnd, int processId, string? windowTitle, List<nint> result)
    {
        if (hwnd == nint.Zero || !IsWindow(hwnd))
        {
            return;
        }

        GetWindowThreadProcessId(hwnd, out var hwndProcessId);
        if (hwndProcessId != processId)
        {
            return;
        }

        if (!string.IsNullOrWhiteSpace(windowTitle))
        {
            var actualTitle = GetWindowTitle(hwnd);
            if (!string.Equals(actualTitle, windowTitle, StringComparison.Ordinal))
            {
                return;
            }
        }

        result.Add(hwnd);
    }

    private static string GetWindowTitle(nint hwnd)
    {
        var length = GetWindowTextLength(hwnd);
        if (length <= 0)
        {
            return string.Empty;
        }

        var builder = new StringBuilder(length + 1);
        _ = GetWindowText(hwnd, builder, builder.Capacity);
        return builder.ToString();
    }

    private delegate bool EnumWindowsProc(nint hwnd, nint lParam);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, nint lParam);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool EnumChildWindows(nint hWndParent, EnumWindowsProc lpEnumFunc, nint lParam);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint GetWindowThreadProcessId(nint hWnd, out int lpdwProcessId);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool IsWindow(nint hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool PostMessage(nint hWnd, int msg, nint wParam, nint lParam);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(nint hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowTextLength(nint hWnd);
}
