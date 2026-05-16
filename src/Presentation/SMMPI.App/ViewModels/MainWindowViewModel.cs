using System.Collections.ObjectModel;
using System.IO;
using System.Threading.Channels;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;
using SMMPI.Domain.Interfaces;
using SMMPI.App.Commands;
using SMMPI.App.Services;
using DomainMediaItem = SMMPI.Domain.Entities.MediaItem;
using DomainMediaType = SMMPI.Domain.Enums.MediaType;
using DomainTouchAction = SMMPI.Domain.Enums.TouchAction;

namespace SMMPI.App.ViewModels;

/// <summary>
/// Coordinates the WPF shell with application services while exposing bindable state to the main window.
/// </summary>
public sealed class MainWindowViewModel : ObservableObject
{
    private readonly IDeviceController _deviceController;
    private readonly IDeviceStreamService _streamService;
    private readonly IMediaLibraryService _mediaLibraryService;
    private readonly IPlatformDetectionService _platformDetectionService;
    private readonly IAndroidAppService _androidAppService;
    private readonly IStreamRecordingService _recordingService;
    private readonly IFolderPicker _folderPicker;
    private readonly ThumbnailService _thumbnailService;
    private readonly CancellationTokenSource _shutdown = new();
    private readonly Channel<StreamFrame> _frames = Channel.CreateBounded<StreamFrame>(new BoundedChannelOptions(1)
    {
        SingleReader = true,
        SingleWriter = false,
        FullMode = BoundedChannelFullMode.DropOldest,
    });

    private MediaItemViewModel? _selectedMedia;
    private ImageSource? _selectedPreview;
    private ImageSource? _streamImage;
    private int _latestFrameWidth;
    private int _latestFrameHeight;
    private string _mediaLibraryFolder = "";
    private string _caseLogFolder = "";
    private string _connectionStatus = "niet verbonden";
    private string _deviceName = "-";
    private string _activeApp = "-";
    private string _statusMessage = "Starten...";
    private string _officerName = "-";
    private string _caseNumber = "-";
    private bool _isRecording;
    private int _busyCount;
    private long _lastMoveSendTicks;
    private int _lastMoveSentX = int.MinValue;
    private int _lastMoveSentY;
    private PlatformTarget? _activePlatform;

    /// <summary>
    /// Wires application services, frame processing, and UI commands for the main operator window.
    /// </summary>
    public MainWindowViewModel(
        IDeviceController deviceController,
        IDeviceStreamService streamService,
        IMediaLibraryService mediaLibraryService,
        IPlatformDetectionService platformDetectionService,
        IAndroidAppService androidAppService,
        IStreamRecordingService recordingService,
        IFolderPicker folderPicker,
        ThumbnailService thumbnailService)
    {
        _deviceController = deviceController;
        _streamService = streamService;
        _mediaLibraryService = mediaLibraryService;
        _platformDetectionService = platformDetectionService;
        _androidAppService = androidAppService;
        _recordingService = recordingService;
        _folderPicker = folderPicker;
        _thumbnailService = thumbnailService;

        _streamService.FrameReceived += (_, frame) => _frames.Writer.TryWrite(frame);
        _ = Task.Run(ProcessFramesAsync, _shutdown.Token);

        BrowseMediaFolderCommand = new AsyncRelayCommand(BrowseMediaFolderAsync);
        BrowseCaseLogFolderCommand = new RelayCommand(BrowseCaseLogFolder);
        RefreshDeviceCommand = new AsyncRelayCommand(RefreshDeviceAsync);
        SendToDeviceCommand = new AsyncRelayCommand(SendToDeviceAsync, () => SelectedMedia is not null && ConnectionStatus.StartsWith("verbonden"));
        ToggleRecordingCommand = new AsyncRelayCommand(ToggleRecordingAsync);
        ExportSessionCommand = new RelayCommand(() => StatusMessage = "Sessiebewijs wordt opgeslagen in de geselecteerde zaakmap.");
    }

    public ObservableCollection<MediaItemViewModel> MediaItems { get; } = [];

    public ICommand BrowseMediaFolderCommand { get; }
    public ICommand BrowseCaseLogFolderCommand { get; }
    public ICommand RefreshDeviceCommand { get; }
    public ICommand SendToDeviceCommand { get; }
    public ICommand ToggleRecordingCommand { get; }
    public ICommand ExportSessionCommand { get; }

    public string OfficerName
    {
        get => _officerName;
        private set => SetProperty(ref _officerName, value);
    }

    public string CaseNumber
    {
        get => _caseNumber;
        private set => SetProperty(ref _caseNumber, value);
    }

    public string MediaLibraryFolder
    {
        get => _mediaLibraryFolder;
        private set => SetProperty(ref _mediaLibraryFolder, value);
    }

    public string CaseLogFolder
    {
        get => _caseLogFolder;
        private set => SetProperty(ref _caseLogFolder, value);
    }

    public MediaItemViewModel? SelectedMedia
    {
        get => _selectedMedia;
        set
        {
            if (SetProperty(ref _selectedMedia, value))
            {
                _ = LoadSelectedPreviewAsync();
                OnPropertyChanged(nameof(SelectedFileName));
                OnPropertyChanged(nameof(SelectedFileType));
                RaiseCommandStates();
            }
        }
    }

    public ImageSource? SelectedPreview
    {
        get => _selectedPreview;
        private set => SetProperty(ref _selectedPreview, value);
    }

    public ImageSource? StreamImage
    {
        get => _streamImage;
        private set => SetProperty(ref _streamImage, value);
    }

    public string SelectedFileName => SelectedMedia?.FileName ?? "Geen bestand geselecteerd";
    public string SelectedFileType => SelectedMedia?.Type ?? "-";

    public string ConnectionStatus
    {
        get => _connectionStatus;
        private set => SetProperty(ref _connectionStatus, value);
    }

    public string DeviceName
    {
        get => _deviceName;
        private set => SetProperty(ref _deviceName, value);
    }

    public string ActiveApp
    {
        get => _activeApp;
        private set => SetProperty(ref _activeApp, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public string RecordButtonText => _isRecording ? "Opname stoppen" : "Scherm opnemen";
    public bool CanSendDeviceKeyboard => ConnectionStatus.StartsWith("verbonden");
    public System.Windows.Input.Cursor AppCursor => Volatile.Read(ref _busyCount) > 0
        ? System.Windows.Input.Cursors.Wait
        : System.Windows.Input.Cursors.Arrow;

    /// <summary>
    /// Opens the session prompt, starts ADB, and attempts initial device connection.
    /// </summary>
    public async Task InitializeAsync()
    {
        using var _ = BeginBusy();
        StatusMessage = "ADB starten...";
        await _deviceController.EnsureAdbServerAsync(_shutdown.Token);

        var prompt = new SessionPrompt { Owner = System.Windows.Application.Current.MainWindow };
        if (prompt.ShowDialog() == true && prompt.Result is not null)
        {
            var result = prompt.Result;
            OfficerName = result.OfficerName;
            CaseNumber = result.CaseNumber;
            CaseLogFolder = Path.Combine(result.CaseRoot, result.CaseNumber);
            Directory.CreateDirectory(CaseLogFolder);
            await _recordingService.StartSessionAsync(result.OfficerName, result.CaseNumber, result.CaseRoot, _shutdown.Token);
        }
        else
        {
            StatusMessage = "Sessie starten geannuleerd.";
            return;
        }

        await RefreshDeviceAsync();
    }

    /// <summary>
    /// Marks the beginning of pointer interaction with the stream preview.
    /// </summary>
    public void BeginStreamInteraction()
    {
    }

    /// <summary>
    /// Marks the end of pointer interaction with the stream preview.
    /// </summary>
    public void EndStreamInteraction()
    {
    }

    /// <summary>
    /// Maps preview coordinates into stream-frame coordinates and forwards the touch action to the device controller.
    /// </summary>
    public async Task SendTouchFromControlAsync(double controlWidth, double controlHeight, double controlX, double controlY, DeviceTouchAction action)
    {
        if (_latestFrameWidth <= 0 || _latestFrameHeight <= 0 || controlWidth <= 0 || controlHeight <= 0)
        {
            return;
        }

        var scale = Math.Min(controlWidth / _latestFrameWidth, controlHeight / _latestFrameHeight);
        var renderedWidth = _latestFrameWidth * scale;
        var renderedHeight = _latestFrameHeight * scale;
        var offsetX = (controlWidth - renderedWidth) / 2;
        var offsetY = (controlHeight - renderedHeight) / 2;
        if (controlX < offsetX || controlY < offsetY || controlX > offsetX + renderedWidth || controlY > offsetY + renderedHeight)
        {
            return;
        }

        var x = (int)Math.Clamp((controlX - offsetX) / scale, 0, _latestFrameWidth - 1);
        var y = (int)Math.Clamp((controlY - offsetY) / scale, 0, _latestFrameHeight - 1);

        if (action == DeviceTouchAction.Move)
        {
            var now = Environment.TickCount64;
            if (now - Volatile.Read(ref _lastMoveSendTicks) < 16 || (x == _lastMoveSentX && y == _lastMoveSentY))
            {
                return;
            }

            Volatile.Write(ref _lastMoveSendTicks, now);
            _lastMoveSentX = x;
            _lastMoveSentY = y;
        }
        else if (action == DeviceTouchAction.Down)
        {
            _lastMoveSentX = int.MinValue;
        }

        var touchAction = action switch
        {
            DeviceTouchAction.Down => DomainTouchAction.Down,
            DeviceTouchAction.Move => DomainTouchAction.Move,
            _ => DomainTouchAction.Up,
        };
        await _deviceController.SendTouchAsync(touchAction, x, y, _shutdown.Token);
    }

    /// <summary>
    /// Sends an Android key event through the C# ADB client.
    /// </summary>
    public Task SendAndroidKeyEventAsync(int androidKeyCode) =>
        _deviceController.SendAndroidKeyEventAsync(androidKeyCode, _shutdown.Token);

    /// <summary>
    /// Sends text input through the C# ADB client.
    /// </summary>
    public Task SendAndroidTextAsync(string text) =>
        _deviceController.SendAndroidTextAsync(text, _shutdown.Token);

    /// <summary>
    /// Sends the current Windows clipboard text to the connected Android device.
    /// </summary>
    public async Task SendClipboardToDeviceAsync()
    {
        if (System.Windows.Clipboard.ContainsText())
        {
            await SendAndroidTextAsync(System.Windows.Clipboard.GetText());
        }
    }

    /// <summary>
    /// Starts or stops screen recording for the current stream preview rectangle.
    /// </summary>
    public async Task ToggleRecordingAsync()
    {
        using var _ = BeginBusy();
        if (_isRecording)
        {
            var path = await _recordingService.StopRecordingAsync(_shutdown.Token);
            _isRecording = false;
            OnPropertyChanged(nameof(RecordButtonText));
            StatusMessage = !string.IsNullOrWhiteSpace(path) ? $"Opname opgeslagen: {path}" : "Opname gestopt.";
            return;
        }

        await _recordingService.StartRecordingAsync(_activePlatform?.Name ?? "UnknownPlatform", _shutdown.Token);
        _isRecording = true;
        OnPropertyChanged(nameof(RecordButtonText));
        StatusMessage = "Opname gestart.";
    }

    /// <summary>
    /// Lets the operator choose a media folder and loads supported media files.
    /// </summary>
    private async Task BrowseMediaFolderAsync()
    {
        var folder = _folderPicker.PickFolder("Selecteer media folder");
        if (folder is null)
        {
            return;
        }

        using var _ = BeginBusy();
        MediaLibraryFolder = folder;
        MediaItems.Clear();
        StatusMessage = "Media laden...";
        foreach (var item in _mediaLibraryService.ScanFolder(folder))
        {
            var type = item.Type == DomainMediaType.Video
                ? AppMediaType.Video
                : AppMediaType.Image;
            var vm = new MediaItemViewModel(new AppMediaItem(item.Path, type));
            MediaItems.Add(vm);
            vm.Thumbnail = await _thumbnailService.CreateThumbnailAsync(vm.Media, _shutdown.Token);
        }

        StatusMessage = $"{MediaItems.Count} mediabestand(en) gevonden.";
    }

    /// <summary>
    /// Updates the displayed case folder path after the operator chooses a folder.
    /// </summary>
    private void BrowseCaseLogFolder()
    {
        var folder = _folderPicker.PickFolder("Selecteer zaakmap");
        if (folder is not null)
        {
            CaseLogFolder = folder;
            StatusMessage = $"Zaakmapweergave ingesteld op {folder}.";
        }
    }

    /// <summary>
    /// Refreshes connected Android devices, selects the first available device, and starts streaming.
    /// </summary>
    private async Task RefreshDeviceAsync()
    {
        using var _ = BeginBusy();
        try
        {
            StatusMessage = "Android-telefoons zoeken...";
            var devices = await _deviceController.GetDevicesAsync(_shutdown.Token);
            var selected = devices.FirstOrDefault(device => device.State == DeviceConnectionState.Connected);
            if (selected is null)
            {
                ConnectionStatus = "niet verbonden";
                DeviceName = "-";
                StatusMessage = "Geen Android-telefoon gevonden. Zet USB-debugging aan en klik op Telefoon vernieuwen.";
                RaiseCommandStates();
                return;
            }

            await _deviceController.ConnectAsync(selected, _shutdown.Token);
            ConnectionStatus = "verbonden (USB)";
            DeviceName = selected.DisplayName;
            StatusMessage = "ADB-stream starten...";
            await _deviceController.StartStreamAsync(_shutdown.Token);
            await RefreshActivePlatformAsync();
            RaiseCommandStates();
        }
        catch (Exception ex)
        {
            ConnectionStatus = "fout";
            StatusMessage = ex.Message;
        }
        finally
        {
            OnPropertyChanged(nameof(CanSendDeviceKeyboard));
        }
    }

    /// <summary>
    /// Refreshes the foreground target app reported by the C# ADB platform detector.
    /// </summary>
    private async Task RefreshActivePlatformAsync()
    {
        try
        {
            var device = _deviceController.SelectedDevice;
            _activePlatform = device is null
                ? null
                : await _platformDetectionService.GetActivePlatformAsync(device.Serial, _shutdown.Token);
            ActiveApp = _activePlatform?.Name ?? "Geen gedetecteerd";
        }
        catch
        {
            ActiveApp = "Onbekend";
        }
    }

    /// <summary>
    /// Sends the selected media item to the connected device using the active platform profile.
    /// </summary>
    private async Task SendToDeviceAsync()
    {
        if (SelectedMedia is null)
        {
            return;
        }

        using var _ = BeginBusy();
        try
        {
            StatusMessage = $"{SelectedMedia.FileName} versturen...";
            var platform = _activePlatform;
            if (platform is null)
            {
                await RefreshActivePlatformAsync();
                platform = _activePlatform;
            }

            if (platform is null)
            {
                StatusMessage = "Geen ondersteund platform op de voorgrond.";
                return;
            }

            var media = new DomainMediaItem(
                SelectedMedia.Media.Path,
                SelectedMedia.Media.Type == AppMediaType.Video ? DomainMediaType.Video : DomainMediaType.Image);
            var result = await _deviceController.SendMediaAsync(media, platform.Profile, _shutdown.Token);
            if (!result.Success)
            {
                StatusMessage = result.Message;
                return;
            }

            var device = _deviceController.SelectedDevice;
            if (device is not null)
            {
                await _androidAppService.TriggerMediaScanAsync(device.Serial, platform.Profile.RemoteMediaPath, _shutdown.Token);
                await _androidAppService.ForceStopAndRelaunchAsync(device.Serial, platform.PackageName, _shutdown.Token);
            }

            StatusMessage = $"Media verstuurd naar {platform.Name}.";
            await RefreshActivePlatformAsync();
        }
        catch (Exception ex)
        {
            StatusMessage = ex.Message;
        }
    }

    /// <summary>
    /// Loads a compact preview image for the selected media item.
    /// </summary>
    private async Task LoadSelectedPreviewAsync()
    {
        using var _ = BeginBusy();
        SelectedPreview = SelectedMedia is null
            ? null
            : await _thumbnailService.CreateThumbnailAsync(SelectedMedia.Media, _shutdown.Token);
    }

    /// <summary>
    /// Consumes latest-only stream frames and publishes frozen WPF images on the UI thread.
    /// </summary>
    private async Task ProcessFramesAsync()
    {
        var reader = _frames.Reader;
        try
        {
            while (await reader.WaitToReadAsync(_shutdown.Token).ConfigureAwait(false))
            {
                while (reader.TryRead(out var frame))
                {
                    ImageSource image;
                    try
                    {
                        image = frame.Format == StreamFrameFormat.Jpeg
                            ? ThumbnailService.LoadJpegBytes(frame.ImageBytes, 720)
                            : ThumbnailService.LoadPngBytes(frame.ImageBytes, 720);
                    }
                    catch
                    {
                        continue;
                    }

                    await System.Windows.Application.Current.Dispatcher.InvokeAsync(
                        () =>
                        {
                            _latestFrameWidth = frame.Width;
                            _latestFrameHeight = frame.Height;
                            StreamImage = image;
                        },
                        DispatcherPriority.Render,
                        _shutdown.Token);
                }
            }
        }
        catch (OperationCanceledException)
        {
        }
    }

    /// <summary>
    /// Refreshes command availability after selected media or connection state changes.
    /// </summary>
    private void RaiseCommandStates()
    {
        if (SendToDeviceCommand is AsyncRelayCommand send)
        {
            send.RaiseCanExecuteChanged();
        }
    }

    /// <summary>
    /// Marks an awaited UI operation as busy so the window shows a wait cursor until the scope ends.
    /// </summary>
    private IDisposable BeginBusy()
    {
        Interlocked.Increment(ref _busyCount);
        OnPropertyChanged(nameof(AppCursor));
        return new BusyScope(this);
    }

    /// <summary>
    /// Restores the busy counter when a loading operation completes.
    /// </summary>
    private sealed class BusyScope : IDisposable
    {
        private MainWindowViewModel? _owner;

        public BusyScope(MainWindowViewModel owner)
        {
            _owner = owner;
        }

        public void Dispose()
        {
            var owner = Interlocked.Exchange(ref _owner, null);
            if (owner is null)
            {
                return;
            }

            Interlocked.Decrement(ref owner._busyCount);
            owner.OnPropertyChanged(nameof(AppCursor));
        }
    }
}
