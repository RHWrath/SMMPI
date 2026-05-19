using System.Collections.ObjectModel;
using System.IO;
using System.Text.Json;
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
    private readonly IAndroidStreamingService _androidStreamingService;
    private readonly IRecordingService _recordingService;
    private readonly IFolderPicker _folderPicker;
    private readonly ThumbnailService _thumbnailService;
    private readonly OperatorSettingsStore _settingsStore;
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
    private string _caseLogFolder = GetDefaultCaseRoot();
    private string _connectionStatus = "niet verbonden";
    private string _deviceName = "-";
    private string _activeApp = "-";
    private string _statusMessage = "Starten...";
    private string _officerName = "";
    private string _caseNumber = "";
    private bool _isRecording;
    private bool _audioEnabled = true;
    private bool _isScrcpyRunning;
    private int? _scrcpyProcessId;
    private string? _scrcpyWindowTitle;
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
        IAndroidStreamingService androidStreamingService,
        IRecordingService recordingService,
        IFolderPicker folderPicker,
        ThumbnailService thumbnailService,
        OperatorSettingsStore settingsStore)
    {
        _deviceController = deviceController;
        _streamService = streamService;
        _mediaLibraryService = mediaLibraryService;
        _platformDetectionService = platformDetectionService;
        _androidAppService = androidAppService;
        _androidStreamingService = androidStreamingService;
        _recordingService = recordingService;
        _folderPicker = folderPicker;
        _thumbnailService = thumbnailService;
        _settingsStore = settingsStore;

        LoadPersistedSettings();

        _streamService.FrameReceived += (_, frame) => _frames.Writer.TryWrite(frame);
        _androidStreamingService.StateChanged += OnAndroidStreamingStateChanged;
        _ = Task.Run(ProcessFramesAsync, _shutdown.Token);

        BrowseMediaFolderCommand = new AsyncRelayCommand(BrowseMediaFolderAsync);
        BrowseCaseLogFolderCommand = new RelayCommand(BrowseCaseLogFolder);
        RefreshDeviceCommand = new AsyncRelayCommand(RefreshDeviceAsync);
        SendToDeviceCommand = new AsyncRelayCommand(SendToDeviceAsync, () => SelectedMedia is not null && ConnectionStatus.StartsWith("verbonden"));
        ToggleRecordingCommand = new AsyncRelayCommand(() => ToggleRecordingAsync("SMMPI Operator", new Rect(0, 0, 1280, 720)));
    }

    public ObservableCollection<MediaItemViewModel> MediaItems { get; } = [];

    public ICommand BrowseMediaFolderCommand { get; }
    public ICommand BrowseCaseLogFolderCommand { get; }
    public ICommand RefreshDeviceCommand { get; }
    public ICommand SendToDeviceCommand { get; }
    public ICommand ToggleRecordingCommand { get; }

    public string OfficerName
    {
        get => _officerName;
        set
        {
            if (SetProperty(ref _officerName, value))
            {
                SavePersistedSettings();
            }
        }
    }

    public string CaseNumber
    {
        get => _caseNumber;
        set
        {
            if (SetProperty(ref _caseNumber, value))
            {
                SavePersistedSettings();
            }
        }
    }

    public string MediaLibraryFolder
    {
        get => _mediaLibraryFolder;
        private set
        {
            if (SetProperty(ref _mediaLibraryFolder, value))
            {
                SavePersistedSettings();
            }
        }
    }

    public string CaseLogFolder
    {
        get => _caseLogFolder;
        private set
        {
            if (SetProperty(ref _caseLogFolder, value))
            {
                SavePersistedSettings();
            }
        }
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
    public bool AudioEnabled
    {
        get => _audioEnabled;
        set
        {
            if (SetProperty(ref _audioEnabled, value) && _deviceController.SelectedDevice is not null && !_isRecording)
            {
                _ = RestartScrcpyStreamAsync();
            }
        }
    }

    public bool IsScrcpyRunning
    {
        get => _isScrcpyRunning;
        private set => SetProperty(ref _isScrcpyRunning, value);
    }

    public int? ScrcpyProcessId
    {
        get => _scrcpyProcessId;
        private set => SetProperty(ref _scrcpyProcessId, value);
    }

    public string? ScrcpyWindowTitle
    {
        get => _scrcpyWindowTitle;
        private set => SetProperty(ref _scrcpyWindowTitle, value);
    }

    public System.Windows.Input.Cursor AppCursor => Volatile.Read(ref _busyCount) > 0
        ? System.Windows.Input.Cursors.Wait
        : System.Windows.Input.Cursors.Arrow;

    /// <summary>
    /// Starts the Python backend, starts ADB, and attempts initial device connection without requiring case details.
    /// </summary>
    public async Task InitializeAsync()
    {
        using var _ = BeginBusy();
        StatusMessage = "ADB starten...";
        await _deviceController.EnsureAdbServerAsync(_shutdown.Token);

        if (Directory.Exists(MediaLibraryFolder))
        {
            await LoadMediaFolderAsync(MediaLibraryFolder);
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
        try
        {
            if (_isRecording)
            {
                var recording = await _recordingService.StopRecordingAsync(_shutdown.Token);
                _isRecording = false;
                OnPropertyChanged(nameof(RecordButtonText));
                StatusMessage = recording is not null
                    ? $"Opname opgeslagen: {recording.OutputPath}. SHA-256: {recording.Sha256Hash}"
                    : "Opname gestopt, maar er is geen opnamebestand gevonden.";
                return;
            }

            var device = _deviceController.SelectedDevice ?? throw new InvalidOperationException("No device selected.");
            var result = await _recordingService.StartRecordingAsync(device, _activePlatform?.Name ?? "UnknownPlatform", AudioEnabled, _shutdown.Token);
            if (!result.Success)
            {
                StatusMessage = result.Message;
                return;
            }

            _isRecording = true;
            OnPropertyChanged(nameof(RecordButtonText));
            StatusMessage = string.IsNullOrWhiteSpace(result.Message) ? "Opname gestart." : result.Message;
        }

        await _backend.SendAsync(
            "start_recording",
            new
            {
                x = (int)Math.Max(0, captureRect.X),
                y = (int)Math.Max(0, captureRect.Y),
                width = (int)Math.Max(2, captureRect.Width),
                height = (int)Math.Max(2, captureRect.Height),
                windowTitle,
                officerName = NormalizeOptionalText(OfficerName),
                caseNumber = NormalizeOptionalText(CaseNumber),
                caseRoot = GetCaseRoot(),
                caseFolder = GetRecordingFolder(),
            },
            _shutdown.Token);
        _isRecording = true;
        OnPropertyChanged(nameof(RecordButtonText));
        StatusMessage = "Opname gestart.";
    }

    /// <summary>
    /// Updates the recording crop after the window or stream preview changes size.
    /// </summary>
    public async Task UpdateRecordingCropAsync(Rect captureRect)
    {
        if (!_isRecording)
        {
            StatusMessage = ex.Message;
        }
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
        await LoadMediaFolderAsync(folder);
    }

    /// <summary>
    /// Loads media from a folder and persists that folder as the current media library.
    /// </summary>
    private async Task LoadMediaFolderAsync(string folder)
    {
        MediaLibraryFolder = folder;
        MediaItems.Clear();
        SelectedMedia = null;
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
        var folder = _folderPicker.PickFolder("Selecteer hoofdmap voor zaken en opnames");
        if (folder is not null)
        {
            CaseLogFolder = folder;
            StatusMessage = $"Zaakmap ingesteld op {folder}.";
        }
    }

    /// <summary>
    /// Returns the root folder used for case data, falling back to the current user's desktop.
    /// </summary>
    private string GetCaseRoot() =>
        string.IsNullOrWhiteSpace(CaseLogFolder) ? GetDefaultCaseRoot() : CaseLogFolder;

    /// <summary>
    /// Resolves the folder where recordings should be written even when no case is filled in.
    /// </summary>
    private string GetRecordingFolder()
    {
        var root = GetCaseRoot();
        var caseNumber = NormalizeOptionalText(CaseNumber);
        return caseNumber is null ? root : Path.Combine(root, SanitizePathSegment(caseNumber));
    }

    /// <summary>
    /// Returns trimmed user text or null when the field has no meaningful value.
    /// </summary>
    private static string? NormalizeOptionalText(string? value)
    {
        var trimmed = value?.Trim();
        return string.IsNullOrWhiteSpace(trimmed) ? null : trimmed;
    }

    /// <summary>
    /// Removes characters that cannot be used in a Windows folder name.
    /// </summary>
    private static string SanitizePathSegment(string value)
    {
        foreach (var invalid in Path.GetInvalidFileNameChars())
        {
            value = value.Replace(invalid, '_');
        }

        return value;
    }

    /// <summary>
    /// Gets the current user's desktop folder without depending on a hardcoded path.
    /// </summary>
    private static string GetDefaultCaseRoot()
    {
        var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        if (!string.IsNullOrWhiteSpace(desktop))
        {
            return desktop;
        }

        var profile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        return string.IsNullOrWhiteSpace(profile) ? Environment.CurrentDirectory : Path.Combine(profile, "Desktop");
    }

    /// <summary>
    /// Restores the operator fields and folders that were saved during an earlier app session.
    /// </summary>
    private void LoadPersistedSettings()
    {
        var settings = _settingsStore.Load();
        _officerName = settings.OfficerName ?? "";
        _caseNumber = settings.CaseNumber ?? "";
        _mediaLibraryFolder = settings.MediaLibraryFolder ?? "";
        _caseLogFolder = string.IsNullOrWhiteSpace(settings.CaseLogFolder)
            ? GetDefaultCaseRoot()
            : settings.CaseLogFolder;
    }

    /// <summary>
    /// Persists the current operator fields and folders for the next app startup.
    /// </summary>
    private void SavePersistedSettings()
    {
        _settingsStore.Save(new OperatorSettings
        {
            OfficerName = OfficerName,
            CaseNumber = CaseNumber,
            MediaLibraryFolder = MediaLibraryFolder,
            CaseLogFolder = CaseLogFolder,
        });
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
                StatusMessage = "Geen Android-telefoon gevonden. Zet USB-debugging aan en klik op Stream verversen.";
                RaiseCommandStates();
                return;
            }

            await _deviceController.ConnectAsync(selected, _shutdown.Token);
            ConnectionStatus = "verbonden (USB)";
            DeviceName = selected.DisplayName;
            StatusMessage = "scrcpy-stream starten...";

            var streamResult = await _androidStreamingService.StartAsync(
                selected,
                new AndroidStreamingOptions(AudioEnabled: AudioEnabled),
                _shutdown.Token);

            if (!streamResult.Success)
            {
                StatusMessage = streamResult.Message;
                RaiseCommandStates();
                return;
            }

            StatusMessage = streamResult.Message;
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
            : await _thumbnailService.CreatePreviewAsync(SelectedMedia.Media, _shutdown.Token);
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

    private async Task RestartScrcpyStreamAsync()
    {
        var device = _deviceController.SelectedDevice;
        if (device is null)
        {
            return;
        }

        try
        {
            await _androidStreamingService.StopAsync(_shutdown.Token);
            var result = await _androidStreamingService.StartAsync(
                device,
                new AndroidStreamingOptions(AudioEnabled: AudioEnabled),
                _shutdown.Token);
            StatusMessage = result.Message;
        }
        catch (Exception ex)
        {
            StatusMessage = ex.Message;
        }
    }

    private void OnAndroidStreamingStateChanged(object? sender, AndroidStreamingState state)
    {
        _ = System.Windows.Application.Current.Dispatcher.InvokeAsync(() =>
        {
            IsScrcpyRunning = state.IsRunning;
            ScrcpyProcessId = state.ProcessId;
            ScrcpyWindowTitle = state.WindowTitle;
            if (!string.IsNullOrWhiteSpace(state.WarningMessage))
            {
                StatusMessage = state.WarningMessage;
            }
        });
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
