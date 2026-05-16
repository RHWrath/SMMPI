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
            _services = ConfigureServices();
            var viewModel = _services.GetRequiredService<MainWindowViewModel>();
            var window = new MainWindow(viewModel);
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
        services.AddSingleton<IAndroidAppService, AndroidAppService>();
        services.AddSingleton<IPlatformDetectionService, AdbPlatformDetectionService>();
        services.AddSingleton<IDeviceStreamService, AdbH264MjpegStreamService>();
        services.AddSingleton<IMediaPipeline, FfmpegMediaPipeline>();
        services.AddSingleton<ISessionLogService, FileSessionLogService>();
        services.AddSingleton<IDeviceController, DeviceController>();
        services.AddSingleton<IMediaLibraryService, MediaLibraryService>();

        services.AddSingleton<IFolderPicker, FolderBrowserPicker>();
        services.AddSingleton<ThumbnailService>();
        services.AddSingleton<IStreamRecordingService, FfmpegStreamRecordingService>();
        services.AddTransient<MainWindowViewModel>();

        return services.BuildServiceProvider();
    }
}
