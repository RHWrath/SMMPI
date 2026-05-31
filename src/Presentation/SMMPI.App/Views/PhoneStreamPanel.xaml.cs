using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using SMMPI.App.Services;
using SMMPI.App.ViewModels;

namespace SMMPI.App.Views;

/// <summary>
/// Reusable phone stream panel that owns device touch and keyboard interaction.
/// </summary>
public partial class PhoneStreamPanel
{
    private Task _pointerDownTask = Task.CompletedTask;

    /// <summary>
    /// Initializes the stream panel and wires capture cleanup.
    /// </summary>
    public PhoneStreamPanel()
    {
        InitializeComponent();
        ScrcpyHost.LostMouseCapture += (_, _) => ViewModel?.EndStreamInteraction();
    }

    private MainWindowViewModel? ViewModel => DataContext as MainWindowViewModel;

    /// <summary>
    /// Gets the stream preview rectangle relative to the supplied visual ancestor.
    /// </summary>
    public Rect GetStreamImageBoundsRelativeTo(Visual ancestor)
    {
        var topLeft = ScrcpyHost.TransformToAncestor(ancestor).Transform(new System.Windows.Point(0, 0));
        return new Rect(topLeft.X, topLeft.Y, ScrcpyHost.ActualWidth, ScrcpyHost.ActualHeight);
    }

    /// <summary>
    /// Starts a touch gesture on the Android stream preview.
    /// </summary>
    private async void StreamImage_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (ViewModel is not { } viewModel)
        {
            return;
        }

        viewModel.BeginStreamInteraction();
        ScrcpyHost.CaptureMouse();
        Keyboard.Focus(ScrcpyHost);
        var point = e.GetPosition(ScrcpyHost);
        _pointerDownTask = viewModel.SendTouchFromControlAsync(
            ScrcpyHost.ActualWidth,
            ScrcpyHost.ActualHeight,
            point.X,
            point.Y,
            DeviceTouchAction.Down);

        try
        {
            await _pointerDownTask;
        }
        catch
        {
            ScrcpyHost.ReleaseMouseCapture();
            viewModel.EndStreamInteraction();
        }
    }

    /// <summary>
    /// Forwards supported special keys and clipboard paste gestures to the Android device.
    /// </summary>
    private async void ScrcpyHost_AndroidKeyDown(object sender, ExternalHostKeyEventArgs e)
    {
        if (ViewModel is not { } viewModel || !viewModel.CanSendDeviceKeyboard)
        {
            return;
        }

        if (e.Key == Key.ImeProcessed)
        {
            return;
        }

        var mods = e.Modifiers;
        if (mods.HasFlag(ModifierKeys.Control) && e.Key == Key.V)
        {
            e.Handled = true;
            await viewModel.SendClipboardToDeviceAsync();
            return;
        }

        if (mods.HasFlag(ModifierKeys.Control) || mods.HasFlag(ModifierKeys.Alt) || mods.HasFlag(ModifierKeys.Windows))
        {
            return;
        }

        if (!TryMapKeyToAndroidKeyCode(e.Key, out var keyCode))
        {
            return;
        }

        e.Handled = true;
        await viewModel.SendAndroidKeyEventAsync(keyCode);
    }

    /// <summary>
    /// Forwards printable text input to the Android device.
    /// </summary>
    private async void ScrcpyHost_AndroidTextInput(object sender, ExternalHostTextEventArgs e)
    {
        if (ViewModel is not { } viewModel || !viewModel.CanSendDeviceKeyboard || string.IsNullOrEmpty(e.Text))
        {
            return;
        }

        var mods = e.Modifiers;
        if (mods.HasFlag(ModifierKeys.Control) || mods.HasFlag(ModifierKeys.Alt) || mods.HasFlag(ModifierKeys.Windows))
        {
            return;
        }

        e.Handled = true;
        await viewModel.SendAndroidTextAsync(e.Text);
    }

    /// <summary>
    /// Sends throttled move events while the operator drags on the stream preview.
    /// </summary>
    private async void StreamImage_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (ViewModel is not { } viewModel || !ScrcpyHost.IsMouseCaptured || e.LeftButton != MouseButtonState.Pressed)
        {
            return;
        }

        try
        {
            await _pointerDownTask.ConfigureAwait(true);
        }
        catch
        {
            return;
        }

        var point = e.GetPosition(ScrcpyHost);
        await viewModel.SendTouchFromControlAsync(ScrcpyHost.ActualWidth, ScrcpyHost.ActualHeight, point.X, point.Y, DeviceTouchAction.Move);
    }

    /// <summary>
    /// Finishes a touch gesture on the Android stream preview.
    /// </summary>
    private async void StreamImage_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (ViewModel is not { } viewModel)
        {
            return;
        }

        try
        {
            try
            {
                await _pointerDownTask.ConfigureAwait(true);
            }
            catch
            {
                return;
            }

            var point = e.GetPosition(ScrcpyHost);
            await viewModel.SendTouchFromControlAsync(ScrcpyHost.ActualWidth, ScrcpyHost.ActualHeight, point.X, point.Y, DeviceTouchAction.Up);
        }
        finally
        {
            _pointerDownTask = Task.CompletedTask;
            ScrcpyHost.ReleaseMouseCapture();
            viewModel.EndStreamInteraction();
        }
    }

    /// <summary>
    /// Maps WPF navigation and editing keys to Android key codes.
    /// </summary>
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
