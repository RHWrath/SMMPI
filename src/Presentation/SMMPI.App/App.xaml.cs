using System.Windows;
using SMMPI.App.Services;
using SMMPI.App.ViewModels;

namespace SMMPI.App;

public partial class App : System.Windows.Application
{
    private PythonBackendClient? _backend;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        try
        {
            _backend = new PythonBackendClient();
            var viewModel = new MainWindowViewModel(_backend, new FolderBrowserPicker(), new ThumbnailService(), new OperatorSettingsStore());
            var window = new SMMPI.App.MainWindow(viewModel);
            window.Show();
            await viewModel.InitializeAsync();
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show(
                $"Opstarten mislukt:\n{ex.Message}",
                "Opstartfout",
                MessageBoxButton.OK,
                MessageBoxImage.Error);

            Shutdown();
        }
    }

    protected override async void OnExit(ExitEventArgs e)
    {
        if (_backend is not null)
        {
            await _backend.DisposeAsync();
        }

        base.OnExit(e);
    }
}
