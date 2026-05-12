namespace WPFTest.ViewModels;

/// <summary>
/// Describes the media categories the WPF shell needs to display and send.
/// </summary>
public enum AppMediaType
{
    Image,
    Video,
}

/// <summary>
/// Lightweight media item used by the WPF shell without depending on the old domain projects.
/// </summary>
public sealed record AppMediaItem(string Path, AppMediaType Type)
{
    public string FileName => System.IO.Path.GetFileName(Path);
}

/// <summary>
/// Touch actions forwarded from the WPF stream preview to the Python scrcpy control channel.
/// </summary>
public enum DeviceTouchAction
{
    Down,
    Move,
    Up,
}
