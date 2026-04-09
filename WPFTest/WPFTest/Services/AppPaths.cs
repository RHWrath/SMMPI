using System.IO;

namespace WPFTest.Services;

/// <summary>
/// Resolves paths to files shipped with the app (output directory).
/// </summary>
internal static class AppPaths
{
    /// <summary>
    /// scrcpy-server binary copied from the Python prototype (VCAM GUI); must stay in sync with stream client.
    /// </summary>
    public static string BundledScrcpyServerPath =>
        Path.Combine(AppContext.BaseDirectory, "Resources", "scrcpy-server-v3.3.4");
}
