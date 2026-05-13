using SMMPI.Application.Services;
using SMMPI.Domain.Entities;
using SMMPI.Domain.Enums;
using SMMPI.Domain.Interfaces;
using SMMPI.Infrastructure.Adb;

namespace SMMPI.Application.Tests;

public class Tests
{
    [Test]
    public void DeviceProfile_SnapchatDefault_MatchesLegacyVirtualCameraContract()
    {
        var profile = DeviceProfile.SnapchatDefault;

        Assert.Multiple(() =>
        {
            Assert.That(profile.RemoteMediaFolder, Is.EqualTo("/storage/emulated/0/DCIM/Camera1/"));
            Assert.That(profile.OutputFileName, Is.EqualTo("virtual.mp4"));
            Assert.That(profile.TargetWidth, Is.EqualTo(1080));
            Assert.That(profile.TargetHeight, Is.EqualTo(1920));
            Assert.That(profile.FramesPerSecond, Is.EqualTo(30));
            Assert.That(profile.MaxVideoDuration, Is.EqualTo(TimeSpan.FromSeconds(60)));
            Assert.That(profile.ImageLoopDuration, Is.EqualTo(TimeSpan.FromSeconds(10)));
            Assert.That(profile.Transform, Is.EqualTo(MediaTransform.RotateMinus90AndMirror));
        });
    }

    [Test]
    public void MediaLibraryService_ClassifiesSupportedMediaAndIgnoresUnsupportedFiles()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);

        try
        {
            File.WriteAllText(Path.Combine(root, "photo.jpg"), string.Empty);
            File.WriteAllText(Path.Combine(root, "clip.mp4"), string.Empty);
            File.WriteAllText(Path.Combine(root, "notes.txt"), string.Empty);

            var items = new MediaLibraryService().ScanFolder(root).ToArray();

            Assert.That(items.Select(item => item.FileName), Is.EquivalentTo(new[] { "photo.jpg", "clip.mp4" }));
            Assert.That(items.Single(item => item.FileName == "photo.jpg").Type, Is.EqualTo(MediaType.Image));
            Assert.That(items.Single(item => item.FileName == "clip.mp4").Type, Is.EqualTo(MediaType.Video));
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Test]
    public void AdbCommandBuilder_AddsSelectedSerialToDeviceCommands()
    {
        var builder = new AdbCommandBuilder(@"C:\Android\platform-tools\adb.exe");

        var push = builder.BuildPush("ABC123", @"C:\temp\virtual.mp4", "/storage/emulated/0/DCIM/Camera1/virtual.mp4");
        var shell = builder.BuildShell("ABC123", "wm", "size");
        var touch = builder.BuildTouch("ABC123", TouchAction.Down, 12, 34);

        Assert.Multiple(() =>
        {
            Assert.That(push.FileName, Is.EqualTo(@"C:\Android\platform-tools\adb.exe"));
            Assert.That(builder.AdbExecutable, Is.EqualTo(@"C:\Android\platform-tools\adb.exe"));
            Assert.That(push.Arguments, Does.StartWith("-s ABC123 push "));
            Assert.That(push.Arguments, Does.Contain("\"C:\\temp\\virtual.mp4\""));
            Assert.That(shell.Arguments, Is.EqualTo("-s ABC123 shell wm size"));
            Assert.That(touch.Arguments, Is.EqualTo("-s ABC123 shell input motionevent DOWN 12 34"));
        });
    }

    [Test]
    public void AdbCommandBuilder_UsesExecOutForScreencapToAvoidPngCorruptionOnWindows()
    {
        var cap = new AdbCommandBuilder(@"C:\Android\platform-tools\adb.exe").BuildScreencap("XYZ");

        Assert.That(cap.FileName, Is.EqualTo(@"C:\Android\platform-tools\adb.exe"));
        Assert.That(cap.Arguments, Is.EqualTo("-s XYZ exec-out screencap -p"));
    }

    [Test]
    public void TouchMapper_MapsRenderedFrameCoordinatesToDeviceResolution()
    {
        var point = TouchMapper.MapToDevice(
            controlWidth: 400,
            controlHeight: 800,
            frameWidth: 200,
            frameHeight: 400,
            deviceWidth: 1080,
            deviceHeight: 1920,
            controlX: 200,
            controlY: 400);

        Assert.That(point, Is.EqualTo(new TouchPoint(540, 960)));
    }

    [Test]
    public void AndroidInputTextEncoder_AppliesAndroidInputTextEscapes()
    {
        var chunks = AndroidInputTextEncoder.EncodeToChunks("a b\nc%d", maxChunkLength: 400).ToArray();

        Assert.That(chunks, Is.EqualTo(new[] { "a%sb%nc%%d" }));
    }

    [Test]
    public void JpegSizeReader_ReadsBaselineSofDimensions()
    {
        // Minimal JPEG: SOF0 with 1x1 dimensions (remaining bytes are filler to satisfy length field).
        var jpeg = new byte[]
        {
            0xFF, 0xD8, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01, 0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xD9,
        };

        var (w, h) = JpegSizeReader.Read(jpeg);
        Assert.That((w, h), Is.EqualTo((1, 1)));
    }

    [Test]
    public async Task DeviceController_SendMediaAsync_ProcessesAndPushesVirtualMp4ToSelectedDevice()
    {
        var adb = new FakeAdbClient();
        var media = new FakeMediaPipeline();
        var stream = new FakeStreamService();
        var log = new FakeSessionLogService();
        var controller = new DeviceController(adb, media, stream, log);
        var device = new AndroidDevice("ABC123", "Google", "Pixel 7", "14", DeviceConnectionState.Connected);
        var selected = new MediaItem(@"C:\cases\photo.jpg", MediaType.Image);

        await controller.ConnectAsync(device, CancellationToken.None);
        var result = await controller.SendMediaAsync(selected, DeviceProfile.SnapchatDefault, CancellationToken.None);

        Assert.Multiple(() =>
        {
            Assert.That(result.Success, Is.True);
            Assert.That(media.LastRequest?.SourcePath, Is.EqualTo(selected.Path));
            Assert.That(adb.LastPush?.Serial, Is.EqualTo("ABC123"));
            Assert.That(adb.LastPush?.RemotePath, Is.EqualTo("/storage/emulated/0/DCIM/Camera1/virtual.mp4"));
            Assert.That(log.Events, Does.Contain("Media pushed to device: virtual.mp4"));
        });
    }

    [Test]
    public void FfmpegCommandBuilder_UsesLegacySnapchatVideoTransformAndAudioSettings()
    {
        var command = new FfmpegCommandBuilder().BuildVideoConversion(
            @"C:\cases\clip.mp4",
            @"C:\temp\virtual.mp4",
            DeviceProfile.SnapchatDefault);

        Assert.Multiple(() =>
        {
            Assert.That(command.Arguments, Does.Contain("-vf \"transpose=2,hflip,scale=1920:-1,crop=1920:1080,fps=30\""));
            Assert.That(command.Arguments, Does.Contain("-c:v libx264"));
            Assert.That(command.Arguments, Does.Contain("-c:a aac"));
            Assert.That(command.Arguments, Does.Contain("-b:a 128k"));
            Assert.That(command.Arguments, Does.Contain("\"C:\\temp\\virtual.mp4\""));
        });
    }

    [Test]
    public void FfmpegCommandBuilder_CreatesImageLoopCommandForConfiguredDuration()
    {
        var command = new FfmpegCommandBuilder().BuildImageLoop(
            @"C:\cases\photo.jpg",
            @"C:\temp\virtual.mp4",
            DeviceProfile.SnapchatDefault);

        Assert.Multiple(() =>
        {
            Assert.That(command.Arguments, Does.Contain("-loop 1"));
            Assert.That(command.Arguments, Does.Contain("-t 10"));
            Assert.That(command.Arguments, Does.Contain("-vf \"transpose=2,hflip,scale=1920:-1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30\""));
            Assert.That(command.Arguments, Does.Contain("-pix_fmt yuv420p"));
        });
    }

    private sealed class FakeAdbClient : IAdbClient
    {
        public (string Serial, string LocalPath, string RemotePath)? LastPush { get; private set; }

        public Task EnsureServerAsync(CancellationToken cancellationToken) => Task.CompletedTask;

        public Task<IReadOnlyList<AndroidDevice>> GetDevicesAsync(CancellationToken cancellationToken) =>
            Task.FromResult<IReadOnlyList<AndroidDevice>>(Array.Empty<AndroidDevice>());

        public Task<string> ShellAsync(string serial, string command, CancellationToken cancellationToken) =>
            Task.FromResult(string.Empty);

        public Task PushAsync(string serial, string localPath, string remotePath, CancellationToken cancellationToken)
        {
            LastPush = (serial, localPath, remotePath);
            return Task.CompletedTask;
        }

        public Task SendTouchAsync(string serial, TouchAction action, int x, int y, CancellationToken cancellationToken) =>
            Task.CompletedTask;

        public Task SendKeyEventAsync(string serial, int androidKeyCode, CancellationToken cancellationToken) =>
            Task.CompletedTask;

        public Task SendTextAsync(string serial, string text, CancellationToken cancellationToken) =>
            Task.CompletedTask;

        public Task<byte[]> CaptureScreenAsync(string serial, CancellationToken cancellationToken) =>
            Task.FromResult(Array.Empty<byte>());
    }

    private sealed class FakeMediaPipeline : IMediaPipeline
    {
        public MediaProcessingRequest? LastRequest { get; private set; }

        public Task<MediaProcessingResult> PrepareAsync(MediaProcessingRequest request, CancellationToken cancellationToken)
        {
            LastRequest = request;
            return Task.FromResult(new MediaProcessingResult(true, @"C:\temp\virtual.mp4", "virtual.mp4", TimeSpan.FromSeconds(10), null));
        }
    }

    private sealed class FakeStreamService : IDeviceStreamService
    {
        public event EventHandler<StreamFrame>? FrameReceived;

        public bool IsRunning { get; private set; }

        public Task StartAsync(AndroidDevice device, CancellationToken cancellationToken)
        {
            IsRunning = true;
            FrameReceived?.Invoke(this, new StreamFrame(Array.Empty<byte>(), 1, 1, DateTimeOffset.UtcNow));
            return Task.CompletedTask;
        }

        public Task StopAsync(CancellationToken cancellationToken)
        {
            IsRunning = false;
            return Task.CompletedTask;
        }
    }

    private sealed class FakeSessionLogService : ISessionLogService
    {
        public List<string> Events { get; } = [];

        public Task LogAsync(string message, CancellationToken cancellationToken)
        {
            Events.Add(message);
            return Task.CompletedTask;
        }
    }
}
