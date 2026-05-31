using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Threading;

namespace SMMPI.App.Services;

public sealed class ExternalWindowHost : HwndHost
{
    private const int WmSetFocus = 0x0007;
    private const int WmKeyDown = 0x0100;
    private const int WmChar = 0x0102;
    private const int WmSysKeyDown = 0x0104;
    private const int WmLButtonDown = 0x0201;
    private const int WmRButtonDown = 0x0204;
    private const int WmMButtonDown = 0x0207;

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
    private readonly WindowProc _externalWindowProc;
    private nint _hostHandle;
    private nint _externalHandle;
    private nint _originalExternalWindowProc;

    public ExternalWindowHost()
    {
        _externalWindowProc = ExternalWindowProc;
        _attachTimer = new DispatcherTimer(DispatcherPriority.Background)
        {
            Interval = TimeSpan.FromMilliseconds(250),
        };
        _attachTimer.Tick += (_, _) => TryAttachExternalWindow();
    }

    public event EventHandler<ExternalHostKeyEventArgs>? AndroidKeyDown;

    public event EventHandler<ExternalHostTextEventArgs>? AndroidTextInput;

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
        RestoreExternalWindowProc();
        if (hwnd.Handle != nint.Zero)
        {
            DestroyWindow(hwnd.Handle);
        }
    }

    protected override void OnWindowPositionChanged(Rect rcBoundingBox)
    {
        base.OnWindowPositionChanged(rcBoundingBox);
        ResizeExternalWindow();
        Dispatcher.BeginInvoke(FocusExternalWindow, DispatcherPriority.Input);
    }

    protected override void OnGotKeyboardFocus(KeyboardFocusChangedEventArgs e)
    {
        base.OnGotKeyboardFocus(e);
        FocusExternalWindow();
    }

    protected override bool TabIntoCore(TraversalRequest request)
    {
        FocusExternalWindow();
        return true;
    }

    protected override bool TranslateAcceleratorCore(ref MSG msg, ModifierKeys modifiers)
    {
        const int wmKeyDown = 0x0100;
        const int wmSysKeyDown = 0x0104;
        const int wmChar = 0x0102;

        if (msg.message is wmKeyDown or wmSysKeyDown)
        {
            var key = KeyInterop.KeyFromVirtualKey(msg.wParam.ToInt32());
            var args = new ExternalHostKeyEventArgs(key, modifiers);
            AndroidKeyDown?.Invoke(this, args);
            if (args.Handled)
            {
                return true;
            }
        }
        else if (msg.message == wmChar)
        {
            var c = (char)msg.wParam.ToInt32();
            if (!char.IsControl(c))
            {
                var args = new ExternalHostTextEventArgs(c.ToString(), modifiers);
                AndroidTextInput?.Invoke(this, args);
                if (args.Handled)
                {
                    return true;
                }
            }
        }

        return base.TranslateAcceleratorCore(ref msg, modifiers);
    }

    protected override nint WndProc(nint hwnd, int msg, nint wParam, nint lParam, ref bool handled)
    {
        if (msg is WmSetFocus or WmLButtonDown or WmRButtonDown or WmMButtonDown)
        {
            FocusExternalWindow();
        }

        return base.WndProc(hwnd, msg, wParam, lParam, ref handled);
    }

    private static void OnWindowTargetChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
    {
        var host = (ExternalWindowHost)d;
        host.RestoreExternalWindowProc();
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
        SubclassExternalWindow();
        ResizeExternalWindow();
        FocusExternalWindow();
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
        FocusExternalWindow();
    }

    private void FocusExternalWindow()
    {
        if (_externalHandle != nint.Zero && IsWindow(_externalHandle))
        {
            SetFocus(_externalHandle);
        }
    }

    private void SubclassExternalWindow()
    {
        if (_externalHandle == nint.Zero || _originalExternalWindowProc != nint.Zero)
        {
            return;
        }

        _originalExternalWindowProc = SetWindowLongPtr(
            _externalHandle,
            WindowLongIndex.GWL_WNDPROC,
            Marshal.GetFunctionPointerForDelegate(_externalWindowProc));
    }

    private void RestoreExternalWindowProc()
    {
        if (_externalHandle != nint.Zero && _originalExternalWindowProc != nint.Zero && IsWindow(_externalHandle))
        {
            SetWindowLongPtr(_externalHandle, WindowLongIndex.GWL_WNDPROC, _originalExternalWindowProc);
        }

        _externalHandle = nint.Zero;
        _originalExternalWindowProc = nint.Zero;
    }

    private nint ExternalWindowProc(nint hwnd, int msg, nint wParam, nint lParam)
    {
        if (TryHandleKeyboardMessage(msg, wParam))
        {
            return nint.Zero;
        }

        return _originalExternalWindowProc == nint.Zero
            ? DefWindowProc(hwnd, msg, wParam, lParam)
            : CallWindowProc(_originalExternalWindowProc, hwnd, msg, wParam, lParam);
    }

    private bool TryHandleKeyboardMessage(int msg, nint wParam)
    {
        if (msg is WmKeyDown or WmSysKeyDown)
        {
            var key = KeyInterop.KeyFromVirtualKey(wParam.ToInt32());
            var args = new ExternalHostKeyEventArgs(key, Keyboard.Modifiers);
            AndroidKeyDown?.Invoke(this, args);
            return args.Handled;
        }

        if (msg == WmChar)
        {
            var c = (char)wParam.ToInt32();
            if (char.IsControl(c))
            {
                return false;
            }

            var args = new ExternalHostTextEventArgs(c.ToString(), Keyboard.Modifiers);
            AndroidTextInput?.Invoke(this, args);
            return args.Handled;
        }

        return false;
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

    private delegate nint WindowProc(nint hwnd, int msg, nint wParam, nint lParam);

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
        public const int GWL_WNDPROC = -4;
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

    [DllImport("user32.dll", SetLastError = true)]
    private static extern nint SetFocus(nint hWnd);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern nint CallWindowProc(nint lpPrevWndFunc, nint hWnd, int msg, nint wParam, nint lParam);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern nint DefWindowProc(nint hWnd, int msg, nint wParam, nint lParam);
}

public sealed class ExternalHostKeyEventArgs : EventArgs
{
    public ExternalHostKeyEventArgs(Key key, ModifierKeys modifiers)
    {
        Key = key;
        Modifiers = modifiers;
    }

    public Key Key { get; }

    public ModifierKeys Modifiers { get; }

    public bool Handled { get; set; }
}

public sealed class ExternalHostTextEventArgs : EventArgs
{
    public ExternalHostTextEventArgs(string text, ModifierKeys modifiers)
    {
        Text = text;
        Modifiers = modifiers;
    }

    public string Text { get; }

    public ModifierKeys Modifiers { get; }

    public bool Handled { get; set; }
}
