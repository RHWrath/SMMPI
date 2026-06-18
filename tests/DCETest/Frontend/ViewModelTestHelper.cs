using Moq;
using SMMPI.App.Commands;
using SMMPI.App.Services;
using SMMPI.App.ViewModels;
using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;
using SMMPI.Domain.Interfaces;

namespace Teststraat.Frontend;

internal sealed class ConnectedViewModelContext
{
    public required MainWindowViewModel ViewModel { get; init; }
    public required Mock<IDeviceController> DeviceController { get; init; }
    public required Mock<IPlatformDetectionService> PlatformDetectionService { get; init; }
    public required Mock<IAndroidAppService> AndroidAppService { get; init; }
    public required AndroidDevice Device { get; init; }
}

internal static class ViewModelTestHelper
{
    public static MainWindowViewModel CreateViewModel(
        Mock<IOperatorSettingsStore>? settingsStore = null,
        Mock<IDeviceController>? deviceController = null,
        Mock<IDeviceStreamService>? streamService = null,
        Mock<IMediaLibraryService>? mediaLibraryService = null,
        Mock<IPlatformDetectionService>? platformDetectionService = null,
        Mock<IAndroidAppService>? androidAppService = null,
        Mock<IAndroidStreamingService>? androidStreamingService = null,
        Mock<IRecordingService>? recordingService = null,
        Mock<IFolderPicker>? folderPicker = null,
        Mock<IThumbnailService>? thumbnailService = null)
    {
        WpfTestHost.EnsureApplication();

        if (settingsStore is null)
        {
            settingsStore = new Mock<IOperatorSettingsStore>();
            settingsStore.Setup(store => store.Load()).Returns(new OperatorSettings());
        }

        if (deviceController is null)
        {
            deviceController = new Mock<IDeviceController>();
            deviceController.Setup(controller => controller.EnsureAdbServerAsync(It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);
            deviceController.Setup(controller => controller.GetDevicesAsync(It.IsAny<CancellationToken>()))
                .ReturnsAsync(Array.Empty<AndroidDevice>());
        }

        streamService ??= new Mock<IDeviceStreamService>();

        if (mediaLibraryService is null)
        {
            mediaLibraryService = new Mock<IMediaLibraryService>();
            mediaLibraryService.Setup(service => service.ScanFolder(It.IsAny<string>()))
                .Returns(Array.Empty<MediaItem>());
        }

        if (platformDetectionService is null)
        {
            platformDetectionService = new Mock<IPlatformDetectionService>();
            platformDetectionService.Setup(service => service.GetActivePlatformAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync((PlatformTarget?)null);
        }

        androidAppService ??= new Mock<IAndroidAppService>();

        if (androidStreamingService is null)
        {
            androidStreamingService = new Mock<IAndroidStreamingService>();
            androidStreamingService.Setup(service => service.StopAsync(It.IsAny<CancellationToken>()))
                .Returns(Task.CompletedTask);
            androidStreamingService.Setup(service => service.DisposeAsync())
                .Returns(ValueTask.CompletedTask);
        }

        recordingService ??= new Mock<IRecordingService>();

        if (folderPicker is null)
        {
            folderPicker = new Mock<IFolderPicker>();
            folderPicker.Setup(picker => picker.PickFolder(It.IsAny<string>()))
                .Returns((string?)null);
        }

        if (thumbnailService is null)
        {
            thumbnailService = new Mock<IThumbnailService>();
            thumbnailService.Setup(service => service.CreateThumbnailAsync(It.IsAny<AppMediaItem>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync((System.Windows.Media.ImageSource?)null);
            thumbnailService.Setup(service => service.CreatePreviewAsync(It.IsAny<AppMediaItem>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync((System.Windows.Media.ImageSource?)null);
        }

        return new MainWindowViewModel(
            deviceController.Object,
            streamService.Object,
            mediaLibraryService.Object,
            platformDetectionService.Object,
            androidAppService.Object,
            androidStreamingService.Object,
            recordingService.Object,
            folderPicker.Object,
            thumbnailService.Object,
            settingsStore.Object);
    }

    public static AndroidDevice CreateConnectedDevice() =>
        new("test-serial", "Google", "Pixel", "14", DeviceConnectionState.Connected);

    public static PlatformTarget CreateSnapchatPlatform() =>
        new("Snapchat", "com.snapchat.android", DeviceProfile.SnapchatDefault);

    public static async Task<ConnectedViewModelContext> CreateConnectedViewModelAsync(
        bool withActivePlatform = true,
        Mock<IRecordingService>? recordingService = null)
    {
        var device = CreateConnectedDevice();
        var deviceController = new Mock<IDeviceController>();
        deviceController.Setup(controller => controller.GetDevicesAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(new[] { device });
        deviceController.Setup(controller => controller.ConnectAsync(device, It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        deviceController.SetupGet(controller => controller.SelectedDevice)
            .Returns(device);

        var androidStreamingService = new Mock<IAndroidStreamingService>();
        androidStreamingService.Setup(service => service.StopAsync(It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        androidStreamingService.Setup(service => service.StartAsync(device, It.IsAny<AndroidStreamingOptions>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(OperationResult.Ok("Stream gestart."));
        androidStreamingService.Setup(service => service.DisposeAsync())
            .Returns(ValueTask.CompletedTask);

        var platformDetectionService = new Mock<IPlatformDetectionService>();
        platformDetectionService.Setup(service => service.GetActivePlatformAsync(device.Serial, It.IsAny<CancellationToken>()))
            .ReturnsAsync(withActivePlatform ? CreateSnapchatPlatform() : null);

        var androidAppService = new Mock<IAndroidAppService>();

        var viewModel = CreateViewModel(
            deviceController: deviceController,
            androidStreamingService: androidStreamingService,
            platformDetectionService: platformDetectionService,
            androidAppService: androidAppService,
            recordingService: recordingService);

        await ((AsyncRelayCommand)viewModel.RefreshDeviceCommand).ExecuteAsync(null);

        return new ConnectedViewModelContext
        {
            ViewModel = viewModel,
            DeviceController = deviceController,
            PlatformDetectionService = platformDetectionService,
            AndroidAppService = androidAppService,
            Device = device,
        };
    }
}
