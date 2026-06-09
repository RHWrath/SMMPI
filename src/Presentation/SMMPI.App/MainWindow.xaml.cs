using System.Runtime.InteropServices;
using DrawingIcon = System.Drawing.Icon;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media.Imaging;
using SMMPI.App.ViewModels;

namespace SMMPI.App;

/// <summary>
/// Interaction logic for the shell that composes the reusable operator panels.
/// </summary>
public partial class MainWindow : Window
{
    private readonly MainWindowViewModel _viewModel;

    /// <summary>
    /// Initializes the main window and keeps shell-level recording crop updates wired to the stream panel.
    /// </summary>
    public MainWindow(MainWindowViewModel viewModel)
    {
        _viewModel = viewModel;
        InitializeComponent();
        DataContext = _viewModel;
        SizeChanged += async (_, _) => await _viewModel.UpdateRecordingCropAsync(GetStreamImageWindowRect());
    }

    /// <summary>
    /// Applies the executable icon to the taskbar (Win11) and keeps title bar in sync with the PE icon.
    /// WPF <see cref="Window.Icon"/> from XAML alone can miss the taskbar when startup work runs before the HWND is ready.
    /// </summary>
    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        ApplyExecutableIconToWindowAndTaskbar();
    }

    private void ApplyExecutableIconToWindowAndTaskbar()
    {
        var executablePath = Environment.ProcessPath;
        if (string.IsNullOrWhiteSpace(executablePath))
        {
            return;
        }

        using var shellIcon = DrawingIcon.ExtractAssociatedIcon(executablePath);
        if (shellIcon is null)
        {
            return;
        }

        var image = Imaging.CreateBitmapSourceFromHIcon(
            shellIcon.Handle,
            Int32Rect.Empty,
            BitmapSizeOptions.FromEmptyOptions());
        image.Freeze();
        Icon = image;

        var hwnd = new WindowInteropHelper(this).Handle;
        if (hwnd == nint.Zero)
        {
            return;
        }

        _ = SendMessage(hwnd, WmSetIcon, IconBig, shellIcon.Handle);
        _ = SendMessage(hwnd, WmSetIcon, IconSmall, shellIcon.Handle);
    }

    private const int WmSetIcon = 0x0080;
    private const int IconSmall = 0;
    private const int IconBig = 1;

    [DllImport("user32.dll", EntryPoint = "SendMessageW", CharSet = CharSet.Unicode)]
    private static extern nint SendMessage(nint hWnd, int msg, int wParam, nint lParam);

    /// <summary>
    /// Toggles recording using the current stream preview bounds as the capture rectangle.
    /// </summary>
    private async void SettingsPanel_ToggleRecordingRequested(object sender, RoutedEventArgs e)
    {
        await _viewModel.ToggleRecordingAsync(Title, GetStreamImageWindowRect());
    }

    /// <summary>
    /// Gets the stream preview rectangle relative to the WPF window for FFmpeg crop updates.
    /// </summary>
    private Rect GetStreamImageWindowRect() =>
        PhoneStreamPanel.GetStreamImageBoundsRelativeTo(this);
}