using System.Windows;
using System.Windows.Input;
using SMMPI.App.Services;
using SMMPI.App.ViewModels;

namespace SMMPI.App;

/// <summary>
/// Interaction logic for MainWindow.xaml.
/// </summary>
public partial class MainWindow : Window
{
    private readonly MainWindowViewModel _viewModel;

    public MainWindow(MainWindowViewModel viewModel)
    {
        _viewModel = viewModel;
        InitializeComponent();
        DataContext = _viewModel;
        ScrcpyHost.AndroidKeyDown += ScrcpyHost_AndroidKeyDown;
        ScrcpyHost.AndroidTextInput += ScrcpyHost_AndroidTextInput;
    }

    private async void ToggleRecording_Click(object sender, RoutedEventArgs e)
    {
        await _viewModel.ToggleRecordingAsync();
    }

    private async void ScrcpyHost_AndroidKeyDown(object? sender, ExternalHostKeyEventArgs e)
    {
        if (!_viewModel.CanSendDeviceKeyboard)
        {
            return;
        }

        if (e.Key == Key.ImeProcessed)
        {
            return;
        }

        if (e.Modifiers.HasFlag(ModifierKeys.Control) && e.Key == Key.V)
        {
            e.Handled = true;
            await _viewModel.SendClipboardToDeviceAsync();
            return;
        }

        if (e.Modifiers.HasFlag(ModifierKeys.Control) ||
            e.Modifiers.HasFlag(ModifierKeys.Alt) ||
            e.Modifiers.HasFlag(ModifierKeys.Windows))
        {
            return;
        }

        if (!TryMapKeyToAndroidKeyCode(e.Key, out var keyCode))
        {
            return;
        }

        e.Handled = true;
        await _viewModel.SendAndroidKeyEventAsync(keyCode);
    }

    private async void ScrcpyHost_AndroidTextInput(object? sender, ExternalHostTextEventArgs e)
    {
        if (!_viewModel.CanSendDeviceKeyboard || string.IsNullOrEmpty(e.Text))
        {
            return;
        }

        if (e.Modifiers.HasFlag(ModifierKeys.Control) ||
            e.Modifiers.HasFlag(ModifierKeys.Alt) ||
            e.Modifiers.HasFlag(ModifierKeys.Windows))
        {
            return;
        }

        e.Handled = true;
        await _viewModel.SendAndroidTextAsync(e.Text);
    }

    private static bool TryMapKeyToAndroidKeyCode(Key key, out int keyCode)
    {
        switch (key)
        {
            case Key.Back:
                keyCode = 67;
                return true;
            case Key.Delete:
                keyCode = 112;
                return true;
            case Key.Return:
            case Key.LineFeed:
                keyCode = 66;
                return true;
            case Key.Tab:
                keyCode = 61;
                return true;
            case Key.Left:
                keyCode = 21;
                return true;
            case Key.Right:
                keyCode = 22;
                return true;
            case Key.Up:
                keyCode = 19;
                return true;
            case Key.Down:
                keyCode = 20;
                return true;
            case Key.Escape:
                keyCode = 111;
                return true;
            default:
                keyCode = 0;
                return false;
        }
    }
}
