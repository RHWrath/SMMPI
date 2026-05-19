using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using SMMPI.Application.Services;
using SMMPI.Domain.Interfaces;
using SMMPI.Infrastructure.Adb;
using SMMPI.Infrastructure.Logging;
using SMMPI.App.Services;
using SMMPI.App.ViewModels;

namespace SMMPI.App;

public partial class App : System.Windows.Application
{
    private ServiceProvider? _services;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        try
        {
            _services = ConfigureServices(););
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
        if (_services is not null)
        {
            await _services.DisposeAsync();
        }

        base.OnExit(e);
    }

    private static ServiceProvider ConfigureServices()
    {
        var services = new ServiceCollection();

        services.AddSingleton<IAdbClient, AdbService>();
        services.AddSingleton<IToolPathService, ToolPathService>();
        services.AddSingleton<ScrcpyCommandBuilder>();
        services.AddSingleton<Sha256FileHasher>();
        services.AddSingleton<IAndroidStreamingService, ScrcpyStreamingService>();
        services.AddSingleton<IAndroidAppService, AndroidAppService>();
        services.AddSingleton<IPlatformDetectionService, AdbPlatformDetectionService>();
        services.AddSingleton<IDeviceStreamService, AdbScreencapStreamService>();
        services.AddSingleton<IMediaPipeline, FfmpegMediaPipeline>();
        services.AddSingleton<ISessionLogService, FileSessionLogService>();
        services.AddSingleton<IDeviceController, DeviceController>();
        services.AddSingleton<IMediaLibraryService, MediaLibraryService>();

        services.AddSingleton<IFolderPicker, FolderBrowserPicker>();
        services.AddSingleton<ThumbnailService>();
        services.AddSingleton<IRecordingService, ScrcpyRecordingService>();
        services.AddTransient<MainWindowViewModel>();

        return services.BuildServiceProvider();
    }
}
