using Moq;
using SMMPI.App.Commands;
using SMMPI.App.Services;
using SMMPI.App.ViewModels;
using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;
using SMMPI.Domain.Interfaces;

namespace Teststraat.Frontend;

[TestClass]
public sealed class MainWindowViewModelTests
{
    [ClassInitialize]
    public static void ClassInitialize(TestContext _)
    {
        WpfTestHost.EnsureApplication();
    }

    [TestMethod]
    public void OfficerName_WhenSet_PersistsThroughSettingsStore()
    {
        var settingsStore = new Mock<IOperatorSettingsStore>();
        settingsStore.Setup(store => store.Load()).Returns(new OperatorSettings());
        var viewModel = ViewModelTestHelper.CreateViewModel(settingsStore: settingsStore);

        viewModel.OfficerName = "Agent Jansen";

        settingsStore.Verify(
            store => store.Save(It.Is<OperatorSettings>(settings => settings.OfficerName == "Agent Jansen")),
            Times.AtLeastOnce);
    }

    [TestMethod]
    public void SendToDeviceCommand_WhenNotConnected_CannotExecute()
    {
        var viewModel = ViewModelTestHelper.CreateViewModel();

        Assert.IsFalse(viewModel.SendToDeviceCommand.CanExecute(null));
    }

    [TestMethod]
    public void SelectedMedia_WhenNull_ShowsDefaultFileName()
    {
        var viewModel = ViewModelTestHelper.CreateViewModel();

        viewModel.SelectedMedia = null;

        Assert.AreEqual("Geen bestand geselecteerd", viewModel.SelectedFileName);
    }

    [TestMethod]
    public void SelectedMedia_WhenSet_UpdatesSelectedFileName()
    {
        var viewModel = ViewModelTestHelper.CreateViewModel();
        var media = new MediaItemViewModel(new AppMediaItem(@"C:\media\photo.jpg", AppMediaType.Image));

        viewModel.SelectedMedia = media;

        Assert.AreEqual("photo.jpg", viewModel.SelectedFileName);
    }

    [TestMethod]
    public async Task RefreshDeviceAsync_WhenConnectedDeviceFound_UpdatesConnectionStatus()
    {
        var context = await ViewModelTestHelper.CreateConnectedViewModelAsync();

        StringAssert.StartsWith(context.ViewModel.ConnectionStatus, "verbonden");
        Assert.AreEqual(context.Device.DisplayName, context.ViewModel.DeviceName);
    }

    [TestMethod]
    public async Task SendToDeviceCommand_WhenConnectedAndMediaSelected_CanExecute()
    {
        var context = await ViewModelTestHelper.CreateConnectedViewModelAsync();
        context.ViewModel.SelectedMedia = new MediaItemViewModel(new AppMediaItem(@"C:\media\photo.jpg", AppMediaType.Image));

        Assert.IsTrue(context.ViewModel.SendToDeviceCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task SendToDeviceAsync_WhenSuccessful_UpdatesStatusAndCallsBackend()
    {
        var context = await ViewModelTestHelper.CreateConnectedViewModelAsync();
        var platform = ViewModelTestHelper.CreateSnapchatPlatform();
        var mediaPath = @"C:\media\photo.jpg";

        context.DeviceController
            .Setup(controller => controller.SendMediaAsync(It.IsAny<MediaItem>(), platform.Profile, It.IsAny<CancellationToken>()))
            .ReturnsAsync(OperationResult.Ok("OK"));

        context.ViewModel.SelectedMedia = new MediaItemViewModel(new AppMediaItem(mediaPath, AppMediaType.Image));

        await ((AsyncRelayCommand)context.ViewModel.SendToDeviceCommand).ExecuteAsync(null);

        Assert.AreEqual("Media verstuurd naar Snapchat.", context.ViewModel.StatusMessage);
        context.DeviceController.Verify(
            controller => controller.SendMediaAsync(
                It.Is<MediaItem>(item => item.Path == mediaPath),
                platform.Profile,
                It.IsAny<CancellationToken>()),
            Times.Once);
        context.AndroidAppService.Verify(
            service => service.TriggerMediaScanAsync(context.Device.Serial, platform.Profile.RemoteMediaPath, It.IsAny<CancellationToken>()),
            Times.Once);
        context.AndroidAppService.Verify(
            service => service.ForceStopAndRelaunchAsync(context.Device.Serial, platform.PackageName, It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [TestMethod]
    public async Task SendToDeviceAsync_WhenNoPlatform_ShowsErrorMessage()
    {
        var context = await ViewModelTestHelper.CreateConnectedViewModelAsync(withActivePlatform: false);
        context.ViewModel.SelectedMedia = new MediaItemViewModel(new AppMediaItem(@"C:\media\photo.jpg", AppMediaType.Image));

        await ((AsyncRelayCommand)context.ViewModel.SendToDeviceCommand).ExecuteAsync(null);

        Assert.AreEqual("Geen ondersteund platform op de voorgrond.", context.ViewModel.StatusMessage);
        context.DeviceController.Verify(
            controller => controller.SendMediaAsync(It.IsAny<MediaItem>(), It.IsAny<DeviceProfile>(), It.IsAny<CancellationToken>()),
            Times.Never);
    }

    [TestMethod]
    public async Task ToggleRecordingAsync_WhenStarted_UpdatesRecordButtonTextAndStatus()
    {
        var recordingService = new Mock<IRecordingService>();
        recordingService.Setup(service => service.StartSessionAsync(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);
        recordingService.Setup(service => service.StartRecordingAsync(It.IsAny<AndroidDevice>(), "Snapchat", true, It.IsAny<CancellationToken>()))
            .ReturnsAsync(OperationResult.Ok(string.Empty));
        recordingService.Setup(service => service.DisposeAsync())
            .Returns(ValueTask.CompletedTask);

        var context = await ViewModelTestHelper.CreateConnectedViewModelAsync(recordingService: recordingService);

        await context.ViewModel.ToggleRecordingAsync();

        Assert.AreEqual("Opname stoppen", context.ViewModel.RecordButtonText);
        Assert.AreEqual("Opname gestart.", context.ViewModel.StatusMessage);
        recordingService.Verify(
            service => service.StartRecordingAsync(context.Device, "Snapchat", true, It.IsAny<CancellationToken>()),
            Times.Once);
    }

    [TestMethod]
    public async Task BrowseMediaFolderAsync_WhenFolderSelected_LoadsMediaItems()
    {
        const string folder = @"C:\media";
        var folderPicker = new Mock<IFolderPicker>();
        folderPicker.Setup(picker => picker.PickFolder("Selecteer media folder"))
            .Returns(folder);

        var mediaLibraryService = new Mock<IMediaLibraryService>();
        mediaLibraryService.Setup(service => service.ScanFolder(folder))
            .Returns(new[]
            {
                new MediaItem(Path.Combine(folder, "photo.jpg"), MediaType.Image),
                new MediaItem(Path.Combine(folder, "clip.mp4"), MediaType.Video),
            });

        var viewModel = ViewModelTestHelper.CreateViewModel(
            folderPicker: folderPicker,
            mediaLibraryService: mediaLibraryService);

        await ((AsyncRelayCommand)viewModel.BrowseMediaFolderCommand).ExecuteAsync(null);

        Assert.HasCount(2, viewModel.MediaItems);
        Assert.AreEqual("2 mediabestand(en) gevonden.", viewModel.StatusMessage);
        mediaLibraryService.Verify(service => service.ScanFolder(folder), Times.Once);
    }
}
