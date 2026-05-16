using System.Windows;
using System.Windows.Input;
using SMMPI.App.ViewModels;

namespace SMMPI.App
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    /// 

    public partial class MainWindow : Window
    {
        private readonly MainWindowViewModel _viewModel;
        /// <summary>
        /// In-flight pointer down send. Mouse down must not await it, otherwise mouse up can run first.
        /// </summary>
        private Task _pointerDownTask = Task.CompletedTask;

        /// <summary>
        /// Initializes the main window and connects UI events to the supplied view model.
        /// </summary>
        public MainWindow(MainWindowViewModel viewModel)
        {
            _viewModel = viewModel;
            InitializeComponent();
            DataContext = _viewModel;
            StreamImage.LostMouseCapture += (_, _) => _viewModel.EndStreamInteraction();
            SizeChanged += async (_, _) => await _viewModel.UpdateRecordingCropAsync(GetStreamImageWindowRect());
        }

        /// <summary>
        /// Starts a touch gesture on the Android stream preview.
        /// </summary>
        private void StreamImage_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            _viewModel.BeginStreamInteraction();
            StreamImage.CaptureMouse();
            Keyboard.Focus(StreamImage);
            var point = e.GetPosition(StreamImage);
            _pointerDownTask = _viewModel.SendTouchFromControlAsync(
                StreamImage.ActualWidth,
                StreamImage.ActualHeight,
                point.X,
                point.Y,
                DeviceTouchAction.Down);
            _ = _pointerDownTask.ContinueWith(
                t =>
                {
                    if (!t.IsFaulted)
                    {
                        return;
                    }

                    _ = Dispatcher.BeginInvoke(() =>
                    {
                        StreamImage.ReleaseMouseCapture();
                        _viewModel.EndStreamInteraction();
                    });
                },
                TaskScheduler.Default);
        }

        /// <summary>
        /// Forwards supported special keys and clipboard paste gestures to the Android device.
        /// </summary>
        private async void StreamImage_PreviewKeyDown(object sender, System.Windows.Input.KeyEventArgs e)
        {
            if (!_viewModel.CanSendDeviceKeyboard)
            {
                return;
            }

            if (e.Key == Key.ImeProcessed)
            {
                return;
            }

            var mods = Keyboard.Modifiers;
            if (mods.HasFlag(ModifierKeys.Control) && e.Key == Key.V)
            {
                e.Handled = true;
                await _viewModel.SendClipboardToDeviceAsync();
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
            await _viewModel.SendAndroidKeyEventAsync(keyCode);
        }

        /// <summary>
        /// Forwards printable text input to the Android device.
        /// </summary>
        private async void StreamImage_PreviewTextInput(object sender, TextCompositionEventArgs e)
        {
            if (!_viewModel.CanSendDeviceKeyboard || string.IsNullOrEmpty(e.Text))
            {
                return;
            }

            var mods = Keyboard.Modifiers;
            if (mods.HasFlag(ModifierKeys.Control) || mods.HasFlag(ModifierKeys.Alt) || mods.HasFlag(ModifierKeys.Windows))
            {
                return;
            }

            e.Handled = true;
            await _viewModel.SendAndroidTextAsync(e.Text);
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

        /// <summary>
        /// Sends throttled move events while the operator drags on the stream preview.
        /// </summary>
        private async void StreamImage_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
        {
            if (!StreamImage.IsMouseCaptured || e.LeftButton != MouseButtonState.Pressed)
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

            var point = e.GetPosition(StreamImage);
            await _viewModel.SendTouchFromControlAsync(StreamImage.ActualWidth, StreamImage.ActualHeight, point.X, point.Y, DeviceTouchAction.Move);
        }

        /// <summary>
        /// Finishes a touch gesture on the Android stream preview.
        /// </summary>
        private async void StreamImage_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
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

                var point = e.GetPosition(StreamImage);
                await _viewModel.SendTouchFromControlAsync(StreamImage.ActualWidth, StreamImage.ActualHeight, point.X, point.Y, DeviceTouchAction.Up);
            }
            finally
            {
                _pointerDownTask = Task.CompletedTask;
                StreamImage.ReleaseMouseCapture();
                _viewModel.EndStreamInteraction();
            }
        }

        /// <summary>
        /// Toggles recording using the current stream preview bounds as the capture rectangle.
        /// </summary>
        private async void ToggleRecording_Click(object sender, RoutedEventArgs e)
        {
            await _viewModel.ToggleRecordingAsync(Title, GetStreamImageWindowRect());
        }

        /// <summary>
        /// Gets the stream preview rectangle relative to the WPF window for FFmpeg crop updates.
        /// </summary>
        private Rect GetStreamImageWindowRect()
        {
            var topLeft = StreamImage.TransformToAncestor(this).Transform(new System.Windows.Point(0, 0));
            return new Rect(topLeft.X, topLeft.Y, StreamImage.ActualWidth, StreamImage.ActualHeight);
        }
    }
}
