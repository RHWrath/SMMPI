using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Threading;

namespace SMMPI.App.Services;

public sealed class ExternalWindowHost : HwndHost
{
    public static readonly DependencyProperty ProcessIdProperty = DependencyProperty.Register(
        nameof(ProcessId),
        typeof(int?),
        typeof(ExternalWindowHost),
        new PropertyMetadata(null, OnWindowTargetChanged));

    public static readonly DependencyProperty WindowTitleProperty = DependencyProperty.Register(
        nameof(WindowTitle),
        typeof(string),
        typeof(ExternalWindowHost),
        new PropertyMetadata(null, OnWindowTargetChanged));

    private readonly DispatcherTimer _attachTimer;
    private nint _hostHandle;
    private nint _externalHandle;

    public ExternalWindowHost()
    {
        _attachTimer = new DispatcherTimer(DispatcherPriority.Background)
        {
            Interval = TimeSpan.FromMilliseconds(250),
        };
        _attachTimer.Tick += (_, _) => TryAttachExternalWindow();
    }

    public int? ProcessId
    {
        get => (int?)GetValue(ProcessIdProperty);
        set => SetValue(ProcessIdProperty, value);
    }

    public string? WindowTitle
    {
        get => (string?)GetValue(WindowTitleProperty);
        set => SetValue(WindowTitleProperty, value);
    }

    protected override HandleRef BuildWindowCore(HandleRef hwndParent)
    {
        _hostHandle = CreateWindowEx(
            0,
            "static",
            string.Empty,
            WindowStyles.WS_CHILD | WindowStyles.WS_VISIBLE | WindowStyles.WS_CLIPSIBLINGS,
            0,
            0,
            Math.Max(1, (int)ActualWidth),
            Math.Max(1, (int)ActualHeight),
            hwndParent.Handle,
            nint.Zero,
            nint.Zero,
            nint.Zero);

        _attachTimer.Start();
        return new HandleRef(this, _hostHandle);
    }

    protected override void DestroyWindowCore(HandleRef hwnd)
    {
        _attachTimer.Stop();
        _externalHandle = nint.Zero;
        if (hwnd.Handle != nint.Zero)
        {
            DestroyWindow(hwnd.Handle);
        }
    }

    protected override void OnWindowPositionChanged(Rect rcBoundingBox)
    {
        base.OnWindowPositionChanged(rcBoundingBox);
        ResizeExternalWindow();
    }

    private static void OnWindowTargetChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
    {
        var host = (ExternalWindowHost)d;
        host._externalHandle = nint.Zero;
        host.TryAttachExternalWindow();
    }

    private void TryAttachExternalWindow()
    {
        if (_hostHandle == nint.Zero || ProcessId is null)
        {
            return;
        }

        if (_externalHandle != nint.Zero && IsWindow(_externalHandle))
        {
            ResizeExternalWindow();
            return;
        }

        var handle = FindTopLevelWindow(ProcessId.Value, WindowTitle);
        if (handle == nint.Zero)
        {
            return;
        }

        _externalHandle = handle;
        SetParent(_externalHandle, _hostHandle);
        var style = GetWindowLongPtr(_externalHandle, WindowLongIndex.GWL_STYLE).ToInt64();
        style &= ~(WindowStyles.WS_CAPTION | WindowStyles.WS_THICKFRAME | WindowStyles.WS_POPUP);
        style |= WindowStyles.WS_CHILD | WindowStyles.WS_VISIBLE;
        SetWindowLongPtr(_externalHandle, WindowLongIndex.GWL_STYLE, new nint(style));
        ResizeExternalWindow();
    }

    private void ResizeExternalWindow()
    {
        if (_externalHandle == nint.Zero || !IsWindow(_externalHandle))
        {
            return;
        }

        MoveWindow(
            _externalHandle,
            0,
            0,
            Math.Max(1, (int)ActualWidth),
            Math.Max(1, (int)ActualHeight),
            true);
    }

    private static nint FindTopLevelWindow(int processId, string? title)
    {
        var result = nint.Zero;
        EnumWindows(
            (hwnd, _) =>
            {
                GetWindowThreadProcessId(hwnd, out var hwndProcessId);
                if (hwndProcessId != processId || !IsWindowVisible(hwnd))
                {
                    return true;
                }

                if (!string.IsNullOrWhiteSpace(title))
                {
                    var actualTitle = GetWindowTitle(hwnd);
                    if (!string.Equals(actualTitle, title, StringComparison.Ordinal))
                    {
                        return true;
                    }
                }

                result = hwnd;
                return false;
            },
            nint.Zero);
        return result;
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

    private static class WindowStyles
    {
        public const int WS_CHILD = 0x40000000;
        public const int WS_VISIBLE = 0x10000000;
        public const int WS_CLIPSIBLINGS = 0x04000000;
        public const int WS_CAPTION = 0x00C00000;
        public const int WS_THICKFRAME = 0x00040000;
        public const int WS_POPUP = unchecked((int)0x80000000);
    }

    private static class WindowLongIndex
    {
        public const int GWL_STYLE = -16;
    }

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern nint CreateWindowEx(
        int dwExStyle,
        string lpClassName,
        string lpWindowName,
        int dwStyle,
        int x,
        int y,
        int nWidth,
        int nHeight,
        nint hWndParent,
        nint hMenu,
        nint hInstance,
        nint lpParam);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool DestroyWindow(nint hwnd);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern nint SetParent(nint hWndChild, nint hWndNewParent);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool MoveWindow(nint hWnd, int x, int y, int nWidth, int nHeight, bool bRepaint);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool IsWindow(nint hWnd);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(nint hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, nint lParam);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint GetWindowThreadProcessId(nint hWnd, out int lpdwProcessId);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(nint hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowTextLength(nint hWnd);

    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW", SetLastError = true)]
    private static extern nint GetWindowLongPtr(nint hWnd, int nIndex);

    [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW", SetLastError = true)]
    private static extern nint SetWindowLongPtr(nint hWnd, int nIndex, nint dwNewLong);
}
