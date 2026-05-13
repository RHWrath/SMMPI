using SMMPI.Domain.Enums;

namespace SMMPI.Domain.Entities;

public sealed record DeviceProfile(
    string Name,
    string RemoteMediaFolder,
    string OutputFileName,
    int TargetWidth,
    int TargetHeight,
    int FramesPerSecond,
    TimeSpan MaxVideoDuration,
    TimeSpan ImageLoopDuration,
    MediaTransform Transform)
{
    public string RemoteMediaPath => $"{RemoteMediaFolder.TrimEnd('/')}/{OutputFileName}";

    public static DeviceProfile SnapchatDefault { get; } = new(
        "Snapchat",
        "/storage/emulated/0/DCIM/Camera1/",
        "virtual.mp4",
        1080,
        1920,
        30,
        TimeSpan.FromSeconds(60),
        TimeSpan.FromSeconds(10),
        MediaTransform.RotateMinus90AndMirror);
}
