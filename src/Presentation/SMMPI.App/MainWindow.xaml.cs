using System.Windows;
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