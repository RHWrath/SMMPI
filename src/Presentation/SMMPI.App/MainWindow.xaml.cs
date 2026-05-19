using System.Windows;
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
    }

    private async void ToggleRecording_Click(object sender, RoutedEventArgs e)
    {
        await _viewModel.ToggleRecordingAsync();
    }
}
